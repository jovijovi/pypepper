from __future__ import annotations

import asyncio
from abc import ABCMeta, abstractmethod
from collections.abc import MutableMapping
from threading import Lock

from pypepper.common.context import Context
from pypepper.common.log import log
from pypepper.common.utils import uuid
from pypepper.scheduler import events
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
    _instance: Dispatcher | None = None
    _init_lock = Lock()

    def __new__(cls):
        with cls._init_lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._lock = Lock()
                inst._processors: MutableMapping[str, Processor] = {}
                cls._instance = inst
            return cls._instance

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
        job._fsm.on(events.INIT)
        job._fsm.on(events.SCHEDULE)

        job.save()
        job.log()

        chan = manager.available(job.channel_id)
        processor = self._available_processor(job.channel_id)
        processor.run(job, chan)


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
    def __init__(self, category: str = None, channel_id: str = 'default'):
        self.id = uuid.new_uuid()
        self.category = category
        self.channel_id = channel_id
        self.context = Context(context_id=uuid.new_uuid())
        self.workflows: list[Workflow] = []
        self._fsm = events.build_scheduler_fsm()

    def save(self):
        log.debug(f"Job saved: id={self.id}, channel_id={self.channel_id}")

    def log(self):
        log.info(f"Job scheduled: id={self.id}, category={self.category}")

    def scheduled(self):
        dispatcher.dispatch(self)
