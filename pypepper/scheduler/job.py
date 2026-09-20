"""Job model, processor, and dispatcher."""

from __future__ import annotations

import asyncio
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, MutableMapping
from threading import Event, Lock
from typing import Any

from pypepper.common.context import Context
from pypepper.common.log import log
from pypepper.common.utils import uuid
from pypepper.common.utils.time import get_utc_datetime
from pypepper.event.interfaces import IEvent
from pypepper.fsm.interfaces import IState
from pypepper.scheduler import events
from pypepper.scheduler.base import IBase
from pypepper.scheduler.channel import SEND_OK, SEND_STOPPED, Channel, manager
from pypepper.scheduler.status import Status
from pypepper.scheduler.store import JobRecord, get_job_store
from pypepper.scheduler.workflow import Workflow

CANCEL_EVENT_KEY = "pypepper.scheduler.cancel_event"
_DISPATCH_SAVE_ATTEMPTS = 3


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
    (channel full or stopped). ``Worker.run_forever`` re-raises. When ``reason`` is
    ``stopped``, leftover queued jobs are drained first; ``full`` stops immediately.
    ``job`` is the unrestored instance (not on the channel).
    """

    def __init__(self, message: str, *, reason: str, job: Job | None = None) -> None:
        super().__init__(message)
        if reason not in ("full", "stopped"):
            raise ValueError(f"JobRedeliveryError.reason must be 'full' or 'stopped', got {reason!r}")
        self.reason = reason
        self.job = job


class JobRequeuedError(RuntimeError):
    """
    Job was restored and put back on the channel after RUN-start persist failure.

    ``Worker.run_forever`` re-raises (does not continue) so supervisors see a non-success
    exit and avoid persist-failure busy-spin; the job remains queued for a later consumer.
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
            "(no running event loop); from async code apply INIT→SCHEDULE, "
            "await Channel.send(job) (returns ok/full/stopped), then job.save(), "
            "and consume with Worker"
        )

    @staticmethod
    async def async_run(
        job: Job,
        chan: Channel,
        *,
        on_enqueued: Callable[[], None] | None = None,
    ) -> None:
        result = await chan.send(job)
        if result == SEND_STOPPED:
            raise ChannelStoppedError(f"channel stopped: channel_id={job.channel_id}, job_id={job.id}")
        if result != SEND_OK:
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
        if not key:
            raise ValueError("invalid key")
        if processor is None:
            raise ValueError("invalid processor")

        with self._lock:
            self._processors[key] = processor

    def _get_processor(self, key: str) -> Processor | None:
        if not key:
            raise ValueError("invalid key")

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
        # Pre-channel apply/enqueue failure must roll back so retry can re-enter.
        # Persist Scheduled only after a successful send so enqueue failure cannot
        # leave a store row (no cleanup delete / ghost).
        prev_state = job._fsm.current()
        prev_status = job.status
        try:
            job.apply_event(events.INIT)
            job.apply_event(events.SCHEDULE)
        except Exception as exc:
            job.restore_lifecycle(prev_state, prev_status)
            log.error(f"Job schedule failed: id={job.id}, error={exc}")
            raise

        job.log()

        # Setup + enqueue: roll back only if the job never landed on the channel.
        # After successful send, persist Scheduled; exceptions are committed-enqueue
        # plus secondary failure (including a failed save after send).
        enqueued = False

        def _mark_enqueued() -> None:
            nonlocal enqueued
            enqueued = True

        try:
            chan = manager.available(job.channel_id)
            processor = self._available_processor(job.channel_id)
            processor.run(job, chan, on_enqueued=_mark_enqueued)
            last_save_exc: Exception | None = None
            for _attempt in range(_DISPATCH_SAVE_ATTEMPTS):
                try:
                    job.save()
                    last_save_exc = None
                    break
                except Exception as save_exc:
                    last_save_exc = save_exc
            if last_save_exc is not None:
                raise last_save_exc
        except Exception as enqueue_exc:
            if enqueued:
                log.error(
                    f"Job post-enqueue error (committed; job may still run): id={job.id}, "
                    f"channel_id={job.channel_id}, error={enqueue_exc}"
                )
                raise
            job.restore_lifecycle(prev_state, prev_status)
            log.error(f"Job enqueue failed: id={job.id}, channel_id={job.channel_id}, error={enqueue_exc}")
            raise


dispatcher = Dispatcher()


class IJob(IBase, metaclass=ABCMeta):
    workflows: list[Workflow]

    @abstractmethod
    def save(self) -> bool:
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
        self._cancel_event = Event()
        self.context.with_value(CANCEL_EVENT_KEY, self._cancel_event)

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
        self.status = self._current_status()

    def cancel(self) -> None:
        """
        Cancel a Scheduled or InProgress job and persist Cancelled.

        On ``save()`` failure the FSM stays Cancelled; retry ``job.save()`` only.
        """
        self._cancel_event.set()
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
            payload=self._workflows_payload(),
        )

    def _workflows_payload(self) -> dict[str, Any] | None:
        if not self.workflows:
            return None
        workflows_out: list[dict[str, Any]] = []
        for workflow in self.workflows:
            tasks_out: list[dict[str, Any]] = []
            for task in workflow.tasks:
                if not task.executor_id:
                    return None
                tasks_out.append(
                    {
                        "id": task.id,
                        "channel_id": task.channel_id,
                        "dag_id": task.dag_id,
                        "fingerprint": task.fingerprint,
                        "name": task.name,
                        "category": task.category,
                        "description": task.description,
                        "tags": [{"key": tag.key, "value": tag.value} for tag in task.tags],
                        "executor_id": task.executor_id,
                        "round_timeout": task.round_timeout,
                        "round_timeout_join": task.round_timeout_join,
                        "round_times": task.round_times,
                        "version": task.version,
                        "retry_count": task.retry_count,
                        "retry_delay": task.retry_delay,
                        "retry_until_completed": task.retry_until_completed,
                        "retry_until_max": task.retry_until_max,
                        "optional": task.optional,
                    }
                )
            workflows_out.append({"tasks": tasks_out})
        return {"workflows": workflows_out}

    @staticmethod
    def _workflows_from_payload(payload: dict[str, Any]) -> list[Workflow]:
        from pypepper.scheduler.executor import executor_registry
        from pypepper.scheduler.tag import Tag
        from pypepper.scheduler.task import Task
        from pypepper.scheduler.workflow import Workflow

        workflows: list[Workflow] = []
        for wf_spec in payload.get("workflows") or []:
            workflow = Workflow()
            for spec in wf_spec.get("tasks") or []:
                executor_id = spec.get("executor_id")
                if not executor_id:
                    raise ValueError("payload task missing executor_id")
                tags = [Tag(key=str(t.get("key", "")), value=str(t.get("value", ""))) for t in spec.get("tags") or []]
                task = Task(
                    channel_id=str(spec["channel_id"]),
                    dag_id=str(spec["dag_id"]),
                    fingerprint=str(spec["fingerprint"]),
                    name=str(spec["name"]),
                    category=str(spec["category"]),
                    description=str(spec.get("description") or ""),
                    tags=tags,
                    executor=executor_registry.resolve(str(executor_id)),
                    round_timeout=int(spec.get("round_timeout") or 0),
                    round_timeout_join=int(spec.get("round_timeout_join") or 0),
                    round_times=int(spec.get("round_times") or 1),
                    version=int(spec.get("version") or 1),
                    retry_count=int(spec.get("retry_count") or 0),
                    retry_delay=int(spec.get("retry_delay") or 0),
                    retry_until_completed=bool(spec.get("retry_until_completed") or False),
                    retry_until_max=int(spec.get("retry_until_max") or 1000),
                    optional=bool(spec.get("optional") or False),
                    executor_id=str(executor_id),
                )
                if spec.get("id"):
                    task.id = str(spec["id"])
                workflow.add_task(task)
            workflows.append(workflow)
        return workflows

    @classmethod
    def from_record(cls, record: JobRecord) -> Job:
        """Rebuild a Job from a store snapshot. Requires registered ``executor_id``s when payload is set."""
        job = cls(category=record.category, channel_id=record.channel_id)
        job.id = record.id
        job.created = record.created
        job.updated = record.updated
        job.version = record.version
        if record.payload:
            job.workflows = cls._workflows_from_payload(record.payload)
        return job

    def save(self) -> bool:
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
            payload=self._workflows_payload(),
        )
        store = get_job_store()
        applied = store.put(record)
        if not applied:
            log.debug(f"Job save skipped stale snapshot: id={self.id}, attempted={status}, version={self.version}")
            return False
        durable = store.get(self.id)
        if durable is not None:
            self.version = durable.version
        self.updated = updated
        log.debug(f"Job saved: id={self.id}, channel_id={self.channel_id}, status={status}")
        return True

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
