"""Channel consumer that runs job workflows."""

from __future__ import annotations

import asyncio
from typing import cast

from pypepper.common.log import log
from pypepper.event.interfaces import IEvent
from pypepper.scheduler import events
from pypepper.scheduler.channel import Channel
from pypepper.scheduler.job import Job


def _transition_and_save_terminal(job: Job, event: IEvent) -> None:
    """
    Apply a terminal FSM event (COMPLETE / FAIL) then persist.

    Work (or failure) has already happened: keep the terminal FSM state even if
    persistence fails. Callers should retry ``job.save()`` only — never re-run
    workflows solely because the terminal snapshot write failed.
    """
    job.apply_event(event)
    job.save()


class Worker:
    """Consume jobs from a channel and run their workflows."""

    def __init__(self, channel: Channel) -> None:
        self.channel = channel

    async def run_once(self) -> Job | None:
        if self.channel.stop:
            return None

        job = cast(Job, await self.channel.receive())
        await self._process(job)
        return job

    async def run_forever(self) -> None:
        while not self.channel.stop:
            await self.run_once()

    async def _process(self, job: Job) -> None:
        prev_state = job._fsm.current()
        prev_status = job.status
        job.apply_event(events.RUN)
        try:
            job.save()
        except Exception as save_exc:
            # Prefer persisting Failed; if that also fails, restore pre-RUN state.
            try:
                job.apply_event(events.FAIL)
                job.save()
            except Exception as fail_save_exc:
                job.restore_lifecycle(prev_state, prev_status)
                log.error(
                    f"Job RUN persist failed: id={job.id}, error={save_exc}; FAIL persist also failed: {fail_save_exc}"
                )
                raise save_exc from fail_save_exc
            log.error(
                f"Job RUN persist failed: id={job.id}, error={save_exc}; "
                f"persisted Failed instead (do not re-run workflows)"
            )
            raise

        try:
            workflows = getattr(job, "workflows", None) or []
            for workflow in workflows:
                # Workflow.run is sync; run it in a worker thread.
                await asyncio.to_thread(workflow.run)
        except Exception as e:
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

        try:
            _transition_and_save_terminal(job, events.COMPLETE)
        except Exception as save_exc:
            log.error(
                f"Job completed but terminal persist failed: id={job.id}; "
                f"retry job.save only (do not re-run workflows): {save_exc}"
            )
            raise
        log.info(f"Job completed: id={job.id}")
