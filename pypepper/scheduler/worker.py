"""Channel consumer that runs job workflows."""

from __future__ import annotations

import asyncio
from typing import NoReturn, cast

from pypepper.common.log import log
from pypepper.event.interfaces import IEvent
from pypepper.fsm.fsm import State
from pypepper.fsm.interfaces import IState
from pypepper.scheduler import events
from pypepper.scheduler.channel import SEND_FULL, SEND_OK, Channel
from pypepper.scheduler.job import Job, JobRedeliveryError, JobRequeuedError
from pypepper.scheduler.status import Status

_FOLLOW_WITHOUT_RUN = frozenset(
    {
        Status.IN_PROGRESS.value,
        Status.FAILED.value,
        Status.COMPLETED.value,
        Status.CANCELLED.value,
    }
)


def _follow_durable_status(job: Job, status: str) -> None:
    job._fsm.restore(State(Status(status)))
    job.status = status


def _force_failed_lifecycle(job: Job) -> None:
    """Move the FSM to Failed. ``FAIL`` is InProgress-only; otherwise restore."""
    if job._current_status() == Status.FAILED.value:
        return
    try:
        job.apply_event(events.FAIL)
    except Exception:
        job._fsm.restore(State(Status.FAILED))
        job.status = Status.FAILED.value


def _persist_failed_snapshot(job: Job) -> None:
    """Prefer a Failed snapshot. Skip (``save()`` False) is persist failure."""
    _force_failed_lifecycle(job)
    if not job.save():
        raise RuntimeError(f"Job Failed persist skipped: id={job.id}")


def _mark_undeliverable_failed(job: Job) -> None:
    """Persist Failed when re-enqueue is impossible (FSM may still be Scheduled)."""
    _force_failed_lifecycle(job)
    try:
        if not job.save():
            log.error(f"Job undeliverable Failed persist skipped: id={job.id}")
    except Exception as exc:
        log.error(f"Job undeliverable Failed persist failed: id={job.id}: {exc}")


def _transition_and_save_terminal(job: Job, event: IEvent) -> None:
    """
    Apply a terminal FSM event (COMPLETE / FAIL) then persist.

    Cancel is applied by ``Job.cancel()``, not here. Work (or failure) has already
    happened: keep the terminal FSM state even if persistence fails. Callers should
    retry ``job.save()`` only — never re-run workflows solely because the terminal
    snapshot write failed.
    """
    job.apply_event(event)
    job.save()


def _ensure_cancelled_persisted(job: Job) -> None:
    """Retry Cancelled snapshot if FSM is cancelled but the store lags."""
    saved = Job.get_saved(job.id)
    if saved is not None and saved.status == Status.CANCELLED.value:
        return
    job.save()


def _ensure_cancelled_persisted_logged(job: Job, *, cause: BaseException | None = None) -> None:
    """Like ``_ensure_cancelled_persisted``, with operator log on persist failure."""
    try:
        _ensure_cancelled_persisted(job)
    except Exception as save_exc:
        log.error(f"Job cancelled but Cancelled persist failed: id={job.id}; retry job.save only: {save_exc}")
        if cause is not None:
            raise save_exc from cause
        raise


class Worker:
    """Consume jobs from a channel and run their workflows."""

    def __init__(self, channel: Channel) -> None:
        self.channel = channel

    async def run_once(self) -> Job | None:
        raw = await self.channel.receive()
        if raw is None:
            return None
        job = cast(Job, raw)
        await self._process(job)
        return job

    async def run_forever(self) -> None:
        stopped_redelivery: JobRedeliveryError | None = None
        while True:
            try:
                job = await self.run_once()
            except JobRequeuedError as e:
                # Job is back on the channel; re-raise so supervisors see failure
                # (do not continue into a persist-failure busy-spin).
                log.error(f"Worker run_forever stopping after re-enqueue: {e!r}")
                raise
            except JobRedeliveryError as e:
                # Full: stop immediately. Stopped: finish draining leftovers, then
                # re-raise outside this handler so supervisors still see non-success
                # (the unrestored job is not on the channel).
                if e.reason == "stopped":
                    log.error(
                        f"Worker run_forever drain continues after redelivery "
                        f"(channel stopped; job not on channel): {e!r}"
                    )
                    if stopped_redelivery is None:
                        stopped_redelivery = e
                    continue
                raise
            except Exception as e:
                # Intentional behavior change vs raise-and-exit: log and continue.
                # Continue-on-error does not redeliver by itself; RUN-start restore
                # paths re-enqueue inside ``_process`` when possible.
                log.error(f"Worker run_forever job error (continuing): {e!r}")
                continue

            if job is None:
                if stopped_redelivery is not None:
                    raise stopped_redelivery
                return

    async def _requeue_after_run_restore(self, job: Job, save_exc: BaseException) -> NoReturn:
        """Re-enqueue after pre-RUN restore, or persist Failed and raise. Never returns normally."""
        result = await self.channel.send(job)
        if result == SEND_OK:
            log.error(f"Job re-enqueued after RUN persist restore: id={job.id}")
            raise JobRequeuedError(
                f"Job re-enqueued after RUN persist restore: id={job.id}, channel_id={job.channel_id}"
            ) from save_exc
        reason = "full" if result == SEND_FULL else "stopped"
        _mark_undeliverable_failed(job)
        raise JobRedeliveryError(
            f"Job RUN persist restore could not re-enqueue "
            f"(channel {reason}): id={job.id}, channel_id={job.channel_id}",
            reason=reason,
            job=job,
        ) from save_exc

    async def _fail_or_restore_after_run_persist(
        self,
        job: Job,
        prev_state: IState | None,
        prev_status: str,
        save_exc: BaseException,
    ) -> None:
        try:
            if job.is_cancelled():
                raise RuntimeError(f"Job already cancelled: id={job.id}")
            _persist_failed_snapshot(job)
        except Exception as fail_save_exc:
            if job.is_cancelled():
                try:
                    _ensure_cancelled_persisted(job)
                except Exception as cancel_save_exc:
                    log.error(
                        f"Job RUN persist failed: id={job.id}, error={save_exc}; "
                        f"cancel won but Cancelled persist failed: {cancel_save_exc}"
                    )
                    raise cancel_save_exc from save_exc
                log.error(
                    f"Job RUN persist failed: id={job.id}, error={save_exc}; "
                    f"cancel already applied (skip restore): {fail_save_exc}"
                )
                raise save_exc from fail_save_exc
            job.restore_lifecycle(prev_state, prev_status)
            log.error(
                f"Job RUN persist failed: id={job.id}, error={save_exc}; FAIL persist also failed: {fail_save_exc}"
            )
            await self._requeue_after_run_restore(job, save_exc)
        log.error(
            f"Job RUN persist failed: id={job.id}, error={save_exc}; persisted Failed instead (do not re-run workflows)"
        )
        raise save_exc

    async def _process(self, job: Job) -> None:
        if job.is_cancelled():
            log.info(f"Job already cancelled, skip: id={job.id}")
            _ensure_cancelled_persisted_logged(job)
            return

        prev_state = job._fsm.current()
        prev_status = job.status

        try:
            if Job.get_saved(job.id) is None and not job.save() and Job.get_saved(job.id) is None:
                raise RuntimeError(f"Job Scheduled persist failed before RUN: id={job.id}")
        except Exception as heal_exc:
            log.error(f"Job missing Scheduled snapshot before RUN: id={job.id}, error={heal_exc}")
            await self._fail_or_restore_after_run_persist(job, prev_state, prev_status, heal_exc)
            return

        job.apply_event(events.RUN)
        try:
            applied = job.save()
        except Exception as save_exc:
            await self._fail_or_restore_after_run_persist(job, prev_state, prev_status, save_exc)
            return

        if not applied:
            durable = Job.get_saved(job.id)
            durable_status = None if durable is None else durable.status
            if durable_status == Status.CANCELLED.value:
                if not job.is_cancelled():
                    job.apply_event(events.CANCEL)
                _ensure_cancelled_persisted_logged(job)
                return
            if durable_status in _FOLLOW_WITHOUT_RUN:
                _follow_durable_status(job, durable_status)
                log.info(f"Job RUN snapshot skipped; following durable {durable_status}: id={job.id}")
                return
            await self._fail_or_restore_after_run_persist(
                job,
                prev_state,
                prev_status,
                RuntimeError(f"Job RUN persist skipped: id={job.id}, durable={durable_status}"),
            )
            return

        try:
            workflows = getattr(job, "workflows", None) or []
            job.share_cancel_event()
            for workflow in workflows:
                if job.is_cancelled():
                    log.info(f"Job cancelled between workflows: id={job.id}")
                    _ensure_cancelled_persisted_logged(job)
                    return
                # Workflow.run is sync; run it in a worker thread.
                await asyncio.to_thread(workflow.run)
        except Exception as e:
            if job.is_cancelled():
                log.info(f"Job cancelled (workflow error ignored): id={job.id}, error={e}")
                _ensure_cancelled_persisted_logged(job, cause=e)
                return
            try:
                _transition_and_save_terminal(job, events.FAIL)
            except Exception as save_exc:
                log.error(
                    f"Job failed: id={job.id}, error={e}; "
                    f"terminal persist also failed (retry job.save only): {save_exc}"
                )
                raise e from save_exc
            log.error(f"Job failed: id={job.id}, error={e}")
            raise

        if job.is_cancelled():
            log.info(f"Job cancelled before complete: id={job.id}")
            _ensure_cancelled_persisted_logged(job)
            return

        try:
            _transition_and_save_terminal(job, events.COMPLETE)
        except Exception as save_exc:
            log.error(
                f"Job completed but terminal persist failed: id={job.id}; "
                f"retry job.save only (do not re-run workflows): {save_exc}"
            )
            raise
        log.info(f"Job completed: id={job.id}")
