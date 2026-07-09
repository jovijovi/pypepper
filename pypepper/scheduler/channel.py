from __future__ import annotations

from asyncio import Queue, QueueFull
from collections.abc import MutableMapping
from threading import Lock
from typing import Any


class Channel:
    def __init__(self, maxsize: int = 0):
        self.stop = False
        self._queue: Queue[Any] = Queue(maxsize)

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
    _instance: ChannelManager | None = None
    _init_lock = Lock()
    _lock: Lock
    _job_channel: MutableMapping[str, Channel]

    def __new__(cls) -> ChannelManager:
        with cls._init_lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._lock = Lock()
                inst._job_channel = {}
                cls._instance = inst
            return cls._instance

    def __init__(self) -> None:
        pass

    def put(self, key: str, chan: Channel) -> None:
        assert key, "invalid key"
        assert chan, "invalid channel"

        with self._lock:
            self._job_channel[key] = chan

    def get(self, key: str) -> Channel | None:
        assert key, "invalid key"

        with self._lock:
            if len(self._job_channel) == 0:
                return None

            return self._job_channel.get(key)

    def remove(self, key: str):
        assert key, "invalid key"

        with self._lock:
            if len(self._job_channel) == 0:
                return None

            return self._job_channel.pop(key)

    def new(self, key: str) -> Channel:
        with self._lock:
            chan = self._job_channel.get(key)
            if chan is None:
                chan = Channel()
                self._job_channel[key] = chan
            return chan

    def available(self, key: str) -> Channel:
        return self.new(key)


manager = ChannelManager()
