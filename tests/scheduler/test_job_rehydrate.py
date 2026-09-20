"""Executor registry, Job.from_record, OCC skip, Worker heal, durable follow."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from threading import Event

import pytest
from pypepper.fsm.fsm import State
from pypepper.scheduler import events
from pypepper.scheduler.channel import Channel, manager
from pypepper.scheduler.executor import CallableExecutor, executor_registry
from pypepper.scheduler.job import CANCEL_EVENT_KEY, Job, JobRequeuedError
from pypepper.scheduler.status import Status
from pypepper.scheduler.store import JobRecord, get_job_store, reset_job_store, set_job_store
from pypepper.scheduler.store.memory import InMemoryJobStore
from pypepper.scheduler.task import Task
from pypepper.scheduler.worker import Worker
from pypepper.scheduler.workflow import Workflow


@pytest.fixture(autouse=True)
def _fresh_job_store():
    from pypepper.common.config import config

    reset_job_store()
    config.mark_scheduler_job_store_applied()
    executor_registry.clear()
    yield
    executor_registry.clear()
    reset_job_store()
    config.mark_scheduler_job_store_applied()


def _task(name: str, executor, *, executor_id: str | None = None, **kwargs) -> Task:
    return Task(
        channel_id="ch",
        dag_id="dag",
        fingerprint=f"fp-{name}",
        name=name,
        category="c",
        description="",
        tags=[],
        executor=executor,
        executor_id=executor_id,
        **kwargs,
    )


def test_to_record_omits_payload_without_executor_id():
    workflow = Workflow()
    workflow.add_task(_task("anon", CallableExecutor(lambda t, c: None)))
    job = Job(category="x", channel_id="payload-none")
    job.workflows = [workflow]
    assert job.to_record().payload is None


def test_from_record_roundtrip_runs_on_worker():
    executed: list[str] = []

    def work(task, context):
        executed.append(task.name)
        return "ok"

    executor_registry.register("echo", CallableExecutor(work))
    workflow = Workflow()
    workflow.add_task(_task("step", CallableExecutor(work), executor_id="echo"))
    job = Job(category="demo", channel_id="rehydrate")
    job.workflows = [workflow]
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    assert job.save() is True
    record = Job.get_saved(job.id)
    assert record is not None
    assert record.payload is not None

    restored = Job.from_record(record)
    assert restored.status == Status.UNKNOWN.value
    assert restored._fsm.current() is not None
    assert restored._fsm.current().value == Status.UNKNOWN
    try:
        restored.scheduled()
        chan = manager.available("rehydrate")
        asyncio.run(Worker(chan).run_once())
        assert executed == ["step"]
    finally:
        manager.remove("rehydrate")


def test_from_record_unknown_executor_id_raises():
    record = JobRecord(
        id="missing-exec",
        category="x",
        channel_id="ch",
        status=Status.SCHEDULED.value,
        created="t0",
        updated="t0",
        payload={
            "workflows": [
                {
                    "tasks": [
                        {
                            "executor_id": "nope",
                            "channel_id": "ch",
                            "dag_id": "d",
                            "fingerprint": "f",
                            "name": "n",
                            "category": "c",
                        }
                    ]
                }
            ]
        },
    )
    with pytest.raises(ValueError, match="unknown executor_id"):
        Job.from_record(record)


def test_put_skips_stale_version():
    store = get_job_store()
    first = JobRecord(
        id="occ-1",
        category="a",
        channel_id="ch",
        status=Status.SCHEDULED.value,
        created="t0",
        updated="t0",
        version=1,
    )
    assert store.put(first) is True
    assert (
        store.put(
            JobRecord(
                id="occ-1",
                category="a",
                channel_id="ch",
                status=Status.IN_PROGRESS.value,
                created="t0",
                updated="t1",
                version=1,
            )
        )
        is True
    )
    got = store.get("occ-1")
    assert got is not None
    assert got.version == 2
    assert got.status == Status.IN_PROGRESS.value
    assert (
        store.put(
            JobRecord(
                id="occ-1",
                category="a",
                channel_id="ch",
                status=Status.COMPLETED.value,
                created="t0",
                updated="t2",
                version=1,
            )
        )
        is False
    )
    skipped = store.get("occ-1")
    assert skipped is not None
    assert skipped.status == Status.IN_PROGRESS.value
    assert skipped.version == 2


def test_job_save_refreshes_version_after_put():
    job = Job(category="x", channel_id="occ-save")
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    assert job.save() is True
    assert job.version == 1
    job.apply_event(events.RUN)
    assert job.save() is True
    assert job.version == 2


def test_apply_event_syncs_status_and_save_skip_keeps_it():
    job = Job(category="x", channel_id="apply-sync")
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    assert job.status == Status.SCHEDULED.value
    get_job_store().put(
        JobRecord(
            id=job.id,
            category=job.category,
            channel_id=job.channel_id,
            status=Status.COMPLETED.value,
            created=job.created,
            updated=job.updated,
            version=1,
        )
    )
    before_updated = job.updated
    before_version = job.version
    assert job.save() is False
    assert job.status == Status.SCHEDULED.value
    assert job.updated == before_updated
    assert job.version == before_version


def test_cancel_sets_context_event():
    job = Job(category="x", channel_id="cancel-token")
    token = job.context.context.get(CANCEL_EVENT_KEY)
    assert isinstance(token, Event)
    assert not token.is_set()
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    job.cancel()
    assert token.is_set()
    assert job.is_cancelled()


@pytest.mark.asyncio
async def test_worker_heals_missing_scheduled_then_runs():
    executed: list[int] = []
    statuses: list[str] = []

    class _RecordingStore(InMemoryJobStore):
        def put(self, record: JobRecord) -> bool:
            statuses.append(record.status)
            return super().put(record)

    def work(task, context):
        executed.append(1)
        return "ok"

    set_job_store(_RecordingStore())
    workflow = Workflow()
    workflow.add_task(_task("heal", CallableExecutor(work)))
    job = Job(category="x", channel_id="heal-ch")
    job.workflows = [workflow]
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    chan = Channel()
    await chan.send(job)
    assert Job.get_saved(job.id) is None
    await Worker(chan).run_once()
    assert executed == [1]
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.COMPLETED.value
    assert statuses[0] == Status.SCHEDULED.value
    assert statuses.index(Status.SCHEDULED.value) < statuses.index(Status.IN_PROGRESS.value)


def test_worker_heals_after_dispatch_save_failure():
    import asyncio

    class _FailPut(InMemoryJobStore):
        def put(self, record: JobRecord) -> bool:
            raise RuntimeError("dispatch-save-failed")

    executed: list[str] = []

    def work(task, context):
        executed.append(task.name)
        return "ok"

    inner = InMemoryJobStore()
    set_job_store(_FailPut())
    channel_id = "heal-after-dispatch"
    manager.remove(channel_id)
    workflow = Workflow()
    workflow.add_task(_task("step", CallableExecutor(work)))
    job = Job(category="x", channel_id=channel_id)
    job.workflows = [workflow]
    try:
        with pytest.raises(RuntimeError, match="dispatch-save-failed"):
            job.scheduled()
        assert Job.get_saved(job.id) is None
        set_job_store(inner)
        chan = manager.get(channel_id)
        assert chan is not None
        asyncio.run(Worker(chan).run_once())
        saved = Job.get_saved(job.id)
        assert saved is not None
        assert saved.status == Status.COMPLETED.value
        assert executed == ["step"]
    finally:
        manager.remove(channel_id)


@pytest.mark.asyncio
async def test_run_skip_when_durable_cancelled_does_not_execute():
    executed: list[int] = []

    def work(task, context):
        executed.append(1)
        return "ok"

    workflow = Workflow()
    workflow.add_task(_task("skip", CallableExecutor(work)))
    job = Job(category="x", channel_id="cancel-race")
    job.workflows = [workflow]
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    job.save()
    job.cancel()
    job.restore_lifecycle(State(Status.SCHEDULED), Status.SCHEDULED.value)
    chan = Channel()
    await chan.send(job)
    await Worker(chan).run_once()
    assert executed == []
    assert job.is_cancelled()
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.CANCELLED.value


def _skip_job(channel_id: str, executed: list[int]) -> Job:
    workflow = Workflow()
    workflow.add_task(_task("skip", CallableExecutor(lambda t, c: executed.append(1) or "ok")))
    job = Job(category="x", channel_id=channel_id)
    job.workflows = [workflow]
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    return job


@pytest.mark.asyncio
async def test_run_skip_when_durable_in_progress_does_not_execute():
    executed: list[int] = []
    job = _skip_job("in-progress-race", executed)
    assert job.save() is True
    seeded = replace(job.to_record(), status=Status.IN_PROGRESS.value, updated="t-run")
    assert get_job_store().put(seeded) is True
    chan = Channel()
    await chan.send(job)
    await Worker(chan).run_once()
    assert executed == []
    assert job.status == Status.IN_PROGRESS.value


@pytest.mark.asyncio
async def test_run_skip_when_durable_completed_does_not_execute():
    executed: list[int] = []
    job = _skip_job("completed-race", executed)
    assert job.save() is True
    seeded = replace(job.to_record(), status=Status.COMPLETED.value, updated="t-done")
    assert get_job_store().put(seeded) is True
    chan = Channel()
    await chan.send(job)
    await Worker(chan).run_once()
    assert executed == []
    assert job.status == Status.COMPLETED.value


@pytest.mark.asyncio
async def test_worker_heal_persist_skip_prefers_failed():
    executed: list[int] = []

    class _SkipScheduled(InMemoryJobStore):
        def put(self, record: JobRecord) -> bool:
            if record.status == Status.SCHEDULED.value:
                return False
            return super().put(record)

    set_job_store(_SkipScheduled())
    job = _skip_job("heal-skip-failed", executed)
    chan = Channel()
    await chan.send(job)
    with pytest.raises(RuntimeError, match="Scheduled persist failed before RUN"):
        await Worker(chan).run_once()
    assert executed == []
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.FAILED.value
    assert chan.length() == 0


@pytest.mark.asyncio
async def test_worker_heal_persist_failure_requeues_when_failed_also_fails():
    executed: list[int] = []

    class _FailAll(InMemoryJobStore):
        def put(self, record: JobRecord) -> bool:
            raise RuntimeError("store-down")

    set_job_store(_FailAll())
    job = _skip_job("heal-requeue", executed)
    chan = Channel()
    await chan.send(job)
    with pytest.raises(JobRequeuedError):
        await Worker(chan).run_once()
    assert executed == []
    assert job.status == Status.SCHEDULED.value
    assert chan.length() == 1


@pytest.mark.asyncio
async def test_run_persist_skip_requeues_when_failed_also_skipped():
    executed: list[int] = []

    class _SkipRunAndFail(InMemoryJobStore):
        def put(self, record: JobRecord) -> bool:
            if record.status in (Status.IN_PROGRESS.value, Status.FAILED.value):
                return False
            return super().put(record)

    set_job_store(_SkipRunAndFail())
    job = _skip_job("run-skip-requeue", executed)
    assert job.save() is True
    chan = Channel()
    await chan.send(job)
    with pytest.raises(JobRequeuedError):
        await Worker(chan).run_once()
    assert executed == []
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.SCHEDULED.value
    assert chan.length() == 1
