from __future__ import annotations

import asyncio
from abc import ABCMeta, abstractmethod
from collections.abc import MutableMapping
from threading import Lock

from pypepper.common.context import Context
from pypepper.common.utils import uuid
from pypepper.scheduler.base import IBase
from pypepper.scheduler.channel import Channel, manager
from pypepper.scheduler.workflow import Workflow


class Processor:
    def run(self, job: Job, chan: Channel):
        asyncio.run(self.async_run(job, chan))

    @staticmethod
    async def async_run(job: Job, chan: Channel):
        await chan.send(job)
        print("[Processor] JobID=", job.id, "Channel Length=", chan.length())


class Dispatcher:
    _lock = Lock()

    _processors: MutableMapping[str, Processor] = {}

    def __init__(self):
        pass

    def _put_processor(self, key: str, processor: Processor) -> None:
        assert key, 'invalid key'
        assert processor, 'invalid processor'

        with self._lock:
            self._processors[key] = processor

    def _get_processor(self, key) -> Processor | None:
        assert key, 'invalid key'

        with self._lock:
            if 0 == len(self._processors):
                return None

            return self._processors.get(key)

    def _new_processor(self, key: str) -> Processor:
        processor = self._get_processor(key)
        if processor is None:
            processor = Processor()
            self._put_processor(key, processor)

        return processor

    def _available_processor(self, key: str) -> Processor:
        return self._new_processor(key)

    def dispatch(self, job: Job):
        # TODO: job status FSM

        # TODO: save job
        job.save()
        # TODO: print log
        job.log()

        chan = manager.available(job.channel_id)
        processor = self._available_processor(job.channel_id)
        processor.run(job, chan)

        # TODO: scheduler

    pass


dispatcher = Dispatcher()


class IJob(IBase, metaclass=ABCMeta):
    workflows: list[Workflow]

    @abstractmethod
    def save(self):
        pass

    @abstractmethod
    def log(self):
        pass

    @abstractmethod
    def scheduled(self):
        pass


class Job(IJob):
    def __init__(self, category: str = None):
        self.id = uuid.new_uuid()
        self.category = category
        self.context = Context(context_id=uuid.new_uuid())

    def save(self):
        # TODO:
        pass

    def log(self):
        # TODO:
        pass

    def scheduled(self):
        dispatcher.dispatch(self)
