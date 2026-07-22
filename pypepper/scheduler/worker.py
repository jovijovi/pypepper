"""Channel consumer that runs job workflows."""

from __future__ import annotations

import asyncio
from typing import cast

from pypepper.common.log import log
from pypepper.event.interfaces import IEvent
from pypepper.scheduler import events
from pypepper.scheduler.channel import Channel
from pypepper.scheduler.job import Job, JobRedeliveryError
from pypepper.scheduler.status import Status


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
        if self.channel.stop:
            return None

        raw = await self.channel.receive()
        if raw is None:
            return None
        job = cast(Job, raw)
        await self._process(job)
        return job

    async def run_forever(self) -> None:
        while not self.channel.stop:
            try:
                job = await self.run_once()
                if job is None:
                    return
            except JobRedeliveryError:
                # Dequeued + restored job could not be put back; stop the loop loudly.
                raise
            except Exception as e:
                # Intentional behavior change vs raise-and-exit: log and continue.
                # Continue-on-error does not redeliver by itself; RUN-start restore
                # paths re-enqueue inside ``_process`` when possible.
                log.error(f"Worker run_forever job error (continuing): {e!r}")

    async def _process(self, job: Job) -> None:
        if job.is_cancelled():
            log.info(f"Job already cancelled, skip: id={job.id}")
            _ensure_cancelled_persisted_logged(job)
            return

        prev_state = job._fsm.current()
        prev_status = job.status
        job.apply_event(events.RUN)
        try:
            job.save()
        except Exception as save_exc:
            # Prefer persisting Failed; if that also fails, restore pre-RUN state
            # unless cancel already won (do not undo Cancelled in-memory).
            try:
                job.apply_event(events.FAIL)
                job.save()
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
                # Job already left the channel; put it back so continue-on-error
                # does not leave a Scheduled snapshot undeliverable.
                requeued = await self.channel.send(job)
                if requeued:
                    log.error(f"Job re-enqueued after RUN persist restore: id={job.id}")
                    raise save_exc from fail_save_exc
                if self.channel.stop:
                    log.error(f"Job RUN persist restore left job off-channel while stopped: id={job.id}")
                    raise save_exc from fail_save_exc
                raise JobRedeliveryError(
                    f"Job RUN persist restore could not re-enqueue "
                    f"(channel full): id={job.id}, channel_id={job.channel_id}"
                ) from save_exc
            log.error(
                f"Job RUN persist failed: id={job.id}, error={save_exc}; "
                f"persisted Failed instead (do not re-run workflows)"
            )
            raise

        try:
            workflows = getattr(job, "workflows", None) or []
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
