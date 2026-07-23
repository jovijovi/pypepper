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
        self._stop = False
        self._queue: Queue[Any] = Queue(maxsize)
        # Wakes a blocked ``receive()`` without consuming queue capacity.
        self._stopped = asyncio.Event()

    @property
    def stop(self) -> bool:
        """True after :meth:`request_stop` (read-only; use ``request_stop()`` to stop)."""
        return self._stop

    async def send(self, value: Any) -> bool:
        """
        Enqueue ``value``.

        Returns ``False`` when the channel is stopped or the bounded queue is full.
        Callers that need the reason must check ``channel.stop`` after a ``False``
        result (``Job.scheduled`` / ``Processor.async_run`` do this).

        Stop is best-effort: a concurrent ``request_stop()`` between the stop check
        and ``put_nowait`` may still enqueue; prefer ``Job.scheduled()`` for typed errors.
        """
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

        Cases:
        1. ``stop`` already set: non-blocking dequeue via ``get_nowait``, or ``None``
           if empty (deterministic drain for direct callers).
        2. Live wait: race queue ``get`` against the stop event; whichever completes
           first wins. An in-flight ``receive()`` (including Worker's) may still return
           a ready item if ``get`` completes in the same turn as stop.
        3. ``Worker.run_once`` checks ``stop`` **before** calling ``receive``, so when
           stop is already set it returns ``None`` without draining (abandons leftovers).

        Do not enqueue ``None`` as a job payload: ``None`` means stop / empty.
        """
        if self.stop:
            try:
                return self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return None

        get_task = asyncio.create_task(self._queue.get())
        stop_task = asyncio.create_task(self._stopped.wait())
        done, pending = await asyncio.wait(
            {get_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        # Prefer a completed get even if it finished while we cancelled siblings.
        if get_task.done() and not get_task.cancelled():
            return get_task.result()
        return None

    def request_stop(self) -> None:
        """Mark the channel stopped and wake a blocked ``receive()`` if needed."""
        self._stop = True
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
