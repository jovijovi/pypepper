"""Async job channels and channel manager."""

from __future__ import annotations

import asyncio
import contextlib
from asyncio import Queue, QueueFull
from collections.abc import MutableMapping
from threading import Lock
from typing import Any, Literal

from pypepper.common.log import log

SendResult = Literal["ok", "full", "stopped"]
SEND_OK: SendResult = "ok"
SEND_FULL: SendResult = "full"
SEND_STOPPED: SendResult = "stopped"


class Channel:
    def __init__(self, maxsize: int = 0) -> None:
        self._stop = False
        self._queue: Queue[Any] = Queue(maxsize)
        # Wakes a blocked ``receive()`` without consuming queue capacity.
        self._stopped = asyncio.Event()
        # Serializes send vs request_stop so a concurrent stop cannot lose an enqueue.
        self._op_lock = Lock()

    @property
    def stop(self) -> bool:
        """True after :meth:`request_stop` (read-only; use ``request_stop()`` to stop)."""
        return self._stop

    async def send(self, value: Any) -> SendResult:
        """
        Enqueue ``value``.

        Returns ``ok``, ``full``, or ``stopped``. The reason is decided under the
        same lock as :meth:`request_stop` (a successful enqueue and a stop-reject
        are mutually exclusive). Prefer ``Job.scheduled()`` for typed errors.
        """
        with self._op_lock:
            if self._stop:
                return SEND_STOPPED
            try:
                self._queue.put_nowait(value)
                return SEND_OK
            except QueueFull:
                return SEND_FULL

    async def receive(self) -> Any | None:
        """
        Wait for the next item, or ``None`` when stop wins and the queue is empty.

        Cases:
        1. ``stop`` already set: non-blocking dequeue via ``get_nowait``, or ``None``
           if empty (deterministic drain).
        2. Live wait: race queue ``get`` against the stop event. A completed ``get``
           is preferred. If stop wins, drain one ready item via ``get_nowait`` so
           leftovers are not abandoned.
        3. ``Worker.run_once`` always calls ``receive`` (including after stop) so
           queued jobs are processed before the consumer exits.

        Do not enqueue ``None`` as a job payload: ``None`` means stop / empty.
        """
        if self.stop:
            try:
                return self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return None

        get_task = asyncio.create_task(self._queue.get())
        stop_task = asyncio.create_task(self._stopped.wait())
        _done, pending = await asyncio.wait(
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
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def request_stop(self) -> None:
        """Mark the channel stopped and wake a blocked ``receive()`` if needed."""
        with self._op_lock:
            if self._stop:
                return
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
        if not key:
            raise ValueError("invalid key")
        if chan is None:
            raise ValueError("invalid channel")

        with self._lock:
            self._job_channel[key] = chan

    def get(self, key: str) -> Channel | None:
        if not key:
            raise ValueError("invalid key")

        with self._lock:
            if len(self._job_channel) == 0:
                return None

            return self._job_channel.get(key)

    def remove(self, key: str) -> Channel | None:
        if not key:
            raise ValueError("invalid key")

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
        if not key:
            raise ValueError("invalid key")
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
