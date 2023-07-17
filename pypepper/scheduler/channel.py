from __future__ import annotations

from asyncio import Queue, QueueFull
from collections.abc import MutableMapping
from threading import Lock
from typing import Any


class Channel:
    stop: bool = False

    def __init__(self, maxsize=0):
        self._queue = Queue(maxsize)

    async def send(self, value: Any) -> bool:
        try:
            self._queue.put_nowait(value)
            return True
        except QueueFull:
            return False

    async def receive(self):
        return await self._queue.get()

    def length(self):
        return self._queue.qsize()


def new(maxsize: int = 0) -> Channel:
    return Channel(maxsize=maxsize)


class ChannelManager:
    _lock = Lock()

    _job_channel: MutableMapping[str, Channel] = {}

    def __init__(self):
        pass

    def put(self, key: str, chan: Channel) -> None:
        assert key, 'invalid key'
        assert chan, 'invalid channel'

        with self._lock:
            self._job_channel[key] = chan

    def get(self, key: str) -> Channel | None:
        assert key, 'invalid key'

        with self._lock:
            if 0 == len(self._job_channel):
                return None

            return self._job_channel.get(key)

    def remove(self, key: str):
        assert key, 'invalid key'

        with self._lock:
            if 0 == len(self._job_channel):
                return None

            self._job_channel.pop(key)

    def new(self, key: str) -> Channel:
        chan = self.get(key)
        if chan is None:
            chan = Channel()
            self.put(key, chan)

        return chan

    def available(self, key: str) -> Channel:
        return self.new(key)


manager = ChannelManager()
