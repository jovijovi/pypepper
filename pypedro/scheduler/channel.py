from asyncio import Queue, QueueFull
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
