"""Executor registry, Job.from_record, OCC skip, Worker heal, durable follow."""

from __future__ import annotations

import asyncio
from threading import Event

import pytest
from pypepper.fsm.fsm import State
from pypepper.scheduler import events
from pypepper.scheduler.channel import Channel, manager
from pypepper.scheduler.executor import CallableExecutor, executor_registry
from pypepper.scheduler.job import CANCEL_EVENT_KEY, Job
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
    assert job.save() is False
    assert job.status == Status.SCHEDULED.value
    assert job.updated == before_updated


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

    def work(task, context):
        executed.append(1)
        return "ok"

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
