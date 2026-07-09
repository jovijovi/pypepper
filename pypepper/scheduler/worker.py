from __future__ import annotations

import asyncio

from pypepper.common.log import log
from pypepper.scheduler import events
from pypepper.scheduler.channel import Channel
from pypepper.scheduler.job import Job


class Worker:
    """Consume jobs from a channel and run their workflows."""

    def __init__(self, channel: Channel):
        self.channel = channel

    async def run_once(self) -> Job | None:
        if self.channel.stop:
            return None

        job = await self.channel.receive()
        await self._process(job)
        return job

    async def run_forever(self):
        while not self.channel.stop:
            await self.run_once()

    async def _process(self, job: Job):
        job._fsm.on(events.RUN)
        try:
            workflows = getattr(job, 'workflows', None) or []
            for workflow in workflows:
                # Workflow.run is sync; offload to thread if needed later
                await asyncio.to_thread(workflow.run)
            job._fsm.on(events.COMPLETE)
            log.info(f"Job completed: id={job.id}")
        except Exception as e:
            job._fsm.on(events.FAIL)
            log.error(f"Job failed: id={job.id}, error={e}")
            raise
