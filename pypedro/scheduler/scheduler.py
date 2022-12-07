from __future__ import annotations

from collections.abc import MutableMapping
from threading import Lock

from pypedro.scheduler.channel import Channel
from pypedro.scheduler.job import Job


class Processor:
    def run(self, job: Job, chan: Channel):
        pass

    pass


class Scheduler:
    _lock = Lock()

    _channel_id: str

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

    def dispatch(self, job: Job, chan: Channel):
        processor = self._available_processor(job.channel_id)
        processor.run(job, chan)

    pass


scheduler = Scheduler()
