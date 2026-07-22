"""Async job channels and channel manager."""

from __future__ import annotations

import asyncio
import contextlib
from asyncio import Queue, QueueFull
from collections.abc import MutableMapping
from threading import Lock
from typing import Any

from pypepper.common.log import log


class Channel:
    def __init__(self, maxsize: int = 0):
        self.stop = False
        self._queue: Queue[Any] = Queue(maxsize)
        # Wakes a blocked ``receive()`` without consuming queue capacity.
        self._stopped = asyncio.Event()

    async def send(self, value: Any) -> bool:
        if self.stop:
            return False
        try:
            self._queue.put_nowait(value)
            return True
        except QueueFull:
            return False

    async def receive(self) -> Any | None:
        """
        Wait for the next item, or ``None`` when stop wins and nothing was dequeued.

        If ``stop`` is already set and the queue is empty, return ``None`` immediately.
        Otherwise race a queue ``get`` against the stop event: whichever completes first
        wins. A pending item may still be returned to a direct ``receive()`` caller when
        both are ready. ``Worker.run_once`` checks ``stop`` before calling ``receive``,
        so it abandons queued items without draining.
        """
        if self.stop and self._queue.empty():
            return None
        get_task = asyncio.create_task(self._queue.get())
        stop_task = asyncio.create_task(self._stopped.wait())
        done, pending = await asyncio.wait(
            {get_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in pending:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        if get_task in done:
            return get_task.result()
        return None

    def request_stop(self) -> None:
        """Mark the channel stopped and wake a blocked ``receive()`` if needed."""
        self.stop = True
        self._stopped.set()

    def length(self) -> int:
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

    def new(self, key: str, maxsize: int = 0) -> Channel:
        """
        Return the channel for ``key``, creating it on first use.

        ``maxsize`` applies only when the channel is created (``0`` = unbounded).
        If the key already exists, the existing channel is returned and ``maxsize``
        is ignored (create bounded channels before Worker/dispatch).
        """
        with self._lock:
            chan = self._job_channel.get(key)
            if chan is None:
                chan = Channel(maxsize=maxsize)
                self._job_channel[key] = chan
            elif maxsize != 0 and chan._queue.maxsize != maxsize:
                log.debug(
                    f"Channel {key!r} already exists (maxsize={chan._queue.maxsize}); "
                    f"ignoring requested maxsize={maxsize}"
                )
            return chan

    def available(self, key: str, maxsize: int = 0) -> Channel:
        """Alias for :meth:`new` (``maxsize`` applies only on first create)."""
        return self.new(key, maxsize=maxsize)


manager = ChannelManager()
