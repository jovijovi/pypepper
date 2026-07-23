"""Job model, processor, and dispatcher."""

from __future__ import annotations

import asyncio
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, MutableMapping
from threading import Lock

from pypepper.common.context import Context
from pypepper.common.log import log
from pypepper.common.utils import uuid
from pypepper.common.utils.time import get_utc_datetime
from pypepper.event.interfaces import IEvent
from pypepper.fsm.interfaces import IState
from pypepper.scheduler import events
from pypepper.scheduler.base import IBase
from pypepper.scheduler.channel import Channel, manager
from pypepper.scheduler.status import Status
from pypepper.scheduler.store import JobRecord, get_job_store
from pypepper.scheduler.workflow import Workflow


class ChannelEnqueueError(RuntimeError):
    """Enqueue rejected before the job lands on the channel (safe to roll back)."""


class ChannelFullError(ChannelEnqueueError):
    """Bounded channel capacity rejection (pre-execution; safe to roll back)."""


class ChannelStoppedError(ChannelEnqueueError):
    """
    Channel was stopped; enqueue rejected (pre-execution; safe to roll back).

    Sibling of :class:`ChannelFullError` (not a subclass): catch this before treating
    :class:`ChannelFullError` as retryable backpressure. Prefer catching
    :class:`ChannelEnqueueError` for any pre-landing rejection.
    """


class JobRedeliveryError(RuntimeError):
    """
    Dequeued job could not be returned to the channel after a RUN-start restore
    (channel full or stopped). ``Worker.run_forever`` re-raises and stops.
    """


class JobRequeuedError(RuntimeError):
    """
    Job was restored and put back on the channel after RUN-start persist failure.

    ``Worker.run_forever`` exits the loop (does not continue immediately) to avoid
    busy-spinning when the store keeps failing; the job remains queued for a later
    consumer.
    """


def _raise_if_transition_failed(resp_error: object) -> None:
    if resp_error is None:
        return
    if isinstance(resp_error, BaseException):
        raise resp_error
    raise RuntimeError(str(resp_error))


class Processor:
    def run(self, job: Job, chan: Channel, *, on_enqueued: Callable[[], None] | None = None) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.async_run(job, chan, on_enqueued=on_enqueued))
            return
        raise RuntimeError(
            "Processor.run / Job.scheduled() must be called from a sync context "
            "(no running event loop); from async code apply INIT→SCHEDULE, call "
            "job.save(), then await Channel.send(job) and consume with Worker"
        )

    @staticmethod
    async def async_run(
        job: Job,
        chan: Channel,
        *,
        on_enqueued: Callable[[], None] | None = None,
    ) -> None:
        ok = await chan.send(job)
        if not ok:
            # Classify after send so a concurrent request_stop is not labeled "full".
            if chan.stop:
                raise ChannelStoppedError(f"channel stopped: channel_id={job.channel_id}, job_id={job.id}")
            raise ChannelFullError(f"channel full: channel_id={job.channel_id}, job_id={job.id}")
        # Job is on the channel: callers must not roll back schedule/store after this.
        if on_enqueued is not None:
            on_enqueued()
        log.debug(f"Job enqueued: id={job.id}, channel_length={chan.length()}")


class Dispatcher:
    _instance: Dispatcher | None = None
    _init_lock = Lock()
    _lock: Lock
    _processors: MutableMapping[str, Processor]

    def __new__(cls) -> Dispatcher:
        with cls._init_lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._lock = Lock()
                inst._processors = {}
                cls._instance = inst
            return cls._instance

    def __init__(self) -> None:
        pass

    def _put_processor(self, key: str, processor: Processor) -> None:
        assert key, "invalid key"
        assert processor, "invalid processor"

        with self._lock:
            self._processors[key] = processor

    def _get_processor(self, key: str) -> Processor | None:
        assert key, "invalid key"

        with self._lock:
            if len(self._processors) == 0:
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

    def dispatch(self, job: Job) -> None:
        # Pre-channel schedule/enqueue failure must roll back so retry can re-enter.
        prev_state = job._fsm.current()
        prev_status = job.status
        try:
            job.apply_event(events.INIT)
            job.apply_event(events.SCHEDULE)
            job.save()
        except Exception as exc:
            job.restore_lifecycle(prev_state, prev_status)
            log.error(f"Job schedule failed: id={job.id}, error={exc}")
            raise

        job.log()

        # Setup + enqueue: roll back only if the job never landed on the channel.
        # After successful send, exceptions are committed-enqueue + secondary failure.
        enqueued = False

        def _mark_enqueued() -> None:
            nonlocal enqueued
            enqueued = True

        try:
            chan = manager.available(job.channel_id)
            processor = self._available_processor(job.channel_id)
            processor.run(job, chan, on_enqueued=_mark_enqueued)
        except Exception as enqueue_exc:
            if enqueued:
                log.error(
                    f"Job post-enqueue error (committed; job may still run): id={job.id}, "
                    f"channel_id={job.channel_id}, error={enqueue_exc}"
                )
                raise
            job.restore_lifecycle(prev_state, prev_status)
            try:
                get_job_store().delete(job.id)
            except Exception as delete_exc:
                log.error(f"Job enqueue cleanup delete failed: id={job.id}, error={delete_exc}")
            log.error(f"Job enqueue failed: id={job.id}, channel_id={job.channel_id}, error={enqueue_exc}")
            raise


dispatcher = Dispatcher()


class IJob(IBase, metaclass=ABCMeta):
    workflows: list[Workflow]

    @abstractmethod
    def save(self) -> None:
        pass

    @abstractmethod
    def log(self) -> None:
        pass

    @abstractmethod
    def scheduled(self) -> None:
        pass

    @abstractmethod
    def cancel(self) -> None:
        pass

    @abstractmethod
    def is_cancelled(self) -> bool:
        pass


class Job(IJob):
    def __init__(self, category: str | None = None, channel_id: str = "default") -> None:
        now = get_utc_datetime()
        self.id = uuid.new_uuid()
        self.category: str | None = category
        self.channel_id = channel_id
        self.context = Context(context_id=uuid.new_uuid())
        self.workflows: list[Workflow] = []
        self._fsm = events.build_scheduler_fsm()
        self.status: str = Status.UNKNOWN.value
        self.created: str = now
        self.updated: str = now
        self.version: int = 1

    def _current_status(self) -> str:
        current = self._fsm.current()
        if current is None:
            return Status.UNKNOWN.value
        value = current.value
        if isinstance(value, Status):
            return value.value
        return str(value)

    def is_cancelled(self) -> bool:
        return self._current_status() == Status.CANCELLED.value

    def restore_lifecycle(self, state: IState | None, status: str) -> None:
        """Restore FSM/`status` after schedule/enqueue failure or RUN-start persist failure."""
        self._fsm.restore(state)
        self.status = status

    def apply_event(self, event: IEvent) -> None:
        """Apply an FSM event or raise if the transition is invalid."""
        resp = self._fsm.on(event)
        _raise_if_transition_failed(resp.error)

    def cancel(self) -> None:
        """
        Cancel a Scheduled or InProgress job and persist Cancelled.

        On ``save()`` failure the FSM stays Cancelled; retry ``job.save()`` only.
        """
        self.apply_event(events.CANCEL)
        self.save()

    def to_record(self) -> JobRecord:
        """Authoritative lifecycle snapshot from the FSM (may lead durable ``status``)."""
        return JobRecord(
            id=self.id,
            category=self.category,
            channel_id=self.channel_id,
            status=self._current_status(),
            created=self.created,
            updated=self.updated,
            workflow_count=len(self.workflows),
            version=self.version,
        )

    def save(self) -> None:
        from pypepper.common.config import config as app_config
        from pypepper.scheduler.store.memory import InMemoryJobStore

        app_config.ensure_scheduler_job_store_applied(
            using_default_memory_store=isinstance(get_job_store(), InMemoryJobStore)
        )
        status = self._current_status()
        updated = get_utc_datetime()
        record = JobRecord(
            id=self.id,
            category=self.category,
            channel_id=self.channel_id,
            status=status,
            created=self.created,
            updated=updated,
            workflow_count=len(self.workflows),
            version=self.version,
        )
        get_job_store().put(record)
        # Mutate in-memory fields only after durable persist succeeds.
        self.status = status
        self.updated = updated
        log.debug(f"Job saved: id={self.id}, channel_id={self.channel_id}, status={self.status}")

    @staticmethod
    def get_saved(job_id: str) -> JobRecord | None:
        from pypepper.common.config import config as app_config
        from pypepper.scheduler.store.memory import InMemoryJobStore

        app_config.ensure_scheduler_job_store_applied(
            using_default_memory_store=isinstance(get_job_store(), InMemoryJobStore)
        )
        return get_job_store().get(job_id)

    def log(self) -> None:
        log.info(f"Job scheduled: id={self.id}, category={self.category}")

    def scheduled(self) -> None:
        dispatcher.dispatch(self)
