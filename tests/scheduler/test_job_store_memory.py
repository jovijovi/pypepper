"""Unit tests for in-memory job store and Job.save lifecycle."""

from __future__ import annotations

import pytest
from pypepper.scheduler import events
from pypepper.scheduler.channel import Channel
from pypepper.scheduler.executor import CallableExecutor
from pypepper.scheduler.job import Job
from pypepper.scheduler.status import Status
from pypepper.scheduler.store import (
    JobRecord,
    configure_job_store,
    get_job_store,
    reset_job_store,
    set_job_store,
)
from pypepper.scheduler.store.memory import InMemoryJobStore
from pypepper.scheduler.task import Task
from pypepper.scheduler.worker import Worker
from pypepper.scheduler.workflow import Workflow


@pytest.fixture(autouse=True)
def _fresh_job_store():
    reset_job_store()
    yield
    reset_job_store()


def test_memory_put_get_list_delete():
    store = get_job_store()
    record = JobRecord(
        id="job-1",
        category="demo",
        channel_id="ch-a",
        status=Status.SCHEDULED.value,
        created="t0",
        updated="t1",
        workflow_count=2,
        version=1,
    )
    store.put(record)
    assert store.get("job-1") == record
    assert store.list(channel_id="ch-a") == [record]
    assert store.list(channel_id="other") == []
    store.delete("job-1")
    assert store.get("job-1") is None


def test_memory_put_upserts():
    store = get_job_store()
    store.put(
        JobRecord(
            id="job-1",
            category="a",
            channel_id="ch",
            status=Status.SCHEDULED.value,
            created="t0",
            updated="t0",
        )
    )
    store.put(
        JobRecord(
            id="job-1",
            category="b",
            channel_id="ch",
            status=Status.COMPLETED.value,
            created="should-not-overwrite",
            updated="t1",
        )
    )
    got = store.get("job-1")
    assert got is not None
    assert got.category == "b"
    assert got.status == Status.COMPLETED.value
    assert got.created == "t0"


def test_scheduled_persists_scheduled_status():
    job = Job(category="Foo", channel_id="mem-sched")
    job.scheduled()
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.SCHEDULED.value
    assert saved.channel_id == "mem-sched"
    assert saved.category == "Foo"


@pytest.mark.asyncio
async def test_worker_persists_completed_status():
    def work(task, context):
        return "ok"

    workflow = Workflow()
    workflow.add_task(
        Task(
            channel_id="ch",
            dag_id="dag",
            fingerprint="fp",
            name="step1",
            category="c",
            description="",
            tags=[],
            executor=CallableExecutor(work),
        )
    )
    job = Job(category="test", channel_id="mem-worker-ok")
    job.workflows = [workflow]
    assert job._fsm.on(events.INIT).error is None
    assert job._fsm.on(events.SCHEDULE).error is None
    job.save()

    chan = Channel()
    await chan.send(job)
    await Worker(chan).run_once()

    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.COMPLETED.value


@pytest.mark.asyncio
async def test_worker_persists_failed_status():
    def boom(task, context):
        raise RuntimeError("boom")

    workflow = Workflow()
    workflow.add_task(
        Task(
            channel_id="ch",
            dag_id="dag",
            fingerprint="fp",
            name="step1",
            category="c",
            description="",
            tags=[],
            executor=CallableExecutor(boom),
            retry_count=0,
        )
    )
    job = Job(category="test", channel_id="mem-worker-fail")
    job.workflows = [workflow]
    assert job._fsm.on(events.INIT).error is None
    assert job._fsm.on(events.SCHEDULE).error is None
    job.save()

    chan = Channel()
    await chan.send(job)
    with pytest.raises(RuntimeError, match="boom"):
        await Worker(chan).run_once()

    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.FAILED.value


def test_set_and_configure_job_store():
    custom = InMemoryJobStore()
    set_job_store(custom)
    assert get_job_store() is custom

    configured = configure_job_store("memory")
    assert isinstance(configured, InMemoryJobStore)
    assert get_job_store() is configured


class _FailingStore(InMemoryJobStore):
    def put(self, record: JobRecord) -> None:
        if record.status in (Status.COMPLETED.value, Status.FAILED.value):
            raise RuntimeError("persist-failed")
        super().put(record)


class _FailOnInProgressStore(InMemoryJobStore):
    def put(self, record: JobRecord) -> None:
        if record.status == Status.IN_PROGRESS.value:
            raise RuntimeError("run-persist-failed")
        super().put(record)


class _AlwaysFailStore(InMemoryJobStore):
    def put(self, record: JobRecord) -> None:
        raise RuntimeError("always-fail")


def _job_with_workflow(executor):
    workflow = Workflow()
    workflow.add_task(
        Task(
            channel_id="ch",
            dag_id="dag",
            fingerprint="fp",
            name="step1",
            category="c",
            description="",
            tags=[],
            executor=CallableExecutor(executor),
            retry_count=0,
        )
    )
    job = Job(category="test", channel_id="mem-save-err")
    job.workflows = [workflow]
    assert job._fsm.on(events.INIT).error is None
    assert job._fsm.on(events.SCHEDULE).error is None
    return job


@pytest.mark.asyncio
async def test_run_save_failure_marks_job_failed():
    set_job_store(_FailOnInProgressStore())
    executed = []

    def work(task, context):
        executed.append(task.name)
        return "ok"

    job = _job_with_workflow(work)
    job.save()
    chan = Channel()
    await chan.send(job)

    with pytest.raises(RuntimeError, match="run-persist-failed"):
        await Worker(chan).run_once()

    assert executed == []
    assert job._fsm.current().value == Status.FAILED
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.FAILED.value


@pytest.mark.asyncio
async def test_complete_save_failure_keeps_completed_fsm():
    set_job_store(_FailingStore())
    executed = []

    def work(task, context):
        executed.append(task.name)
        return "ok"

    job = _job_with_workflow(work)
    job.save()
    chan = Channel()
    await chan.send(job)

    with pytest.raises(RuntimeError, match="persist-failed"):
        await Worker(chan).run_once()

    # Work finished: keep Completed; retry job.save() only (store may still be InProgress).
    assert executed == ["step1"]
    assert job._fsm.current().value == Status.COMPLETED
    assert job.status == Status.IN_PROGRESS.value
    assert job.to_record().status == Status.COMPLETED.value
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.IN_PROGRESS.value

    # Retry save only (no re-run) after store accepts COMPLETED.
    reset_job_store()
    # Seed last durable InProgress then overwrite via save from Completed FSM.
    get_job_store().put(
        JobRecord(
            id=job.id,
            category=job.category,
            channel_id=job.channel_id,
            status=Status.IN_PROGRESS.value,
            created=job.created,
            updated=job.updated,
            workflow_count=1,
            version=1,
        )
    )
    job.save()
    assert executed == ["step1"]
    assert Job.get_saved(job.id).status == Status.COMPLETED.value
    assert job.status == Status.COMPLETED.value


@pytest.mark.asyncio
async def test_fail_path_save_failure_keeps_failed_fsm():
    set_job_store(_FailingStore())

    def boom(task, context):
        raise RuntimeError("boom")

    job = _job_with_workflow(boom)
    job.save()
    chan = Channel()
    await chan.send(job)

    with pytest.raises(RuntimeError, match="boom") as exc_info:
        await Worker(chan).run_once()

    assert "persist-failed" not in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert "persist-failed" in str(exc_info.value.__cause__)
    # Terminal failure kept; retry job.save() only.
    assert job._fsm.current().value == Status.FAILED
    assert job.status == Status.IN_PROGRESS.value
    assert job.to_record().status == Status.FAILED.value
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.IN_PROGRESS.value

    reset_job_store()
    get_job_store().put(
        JobRecord(
            id=job.id,
            category=job.category,
            channel_id=job.channel_id,
            status=Status.IN_PROGRESS.value,
            created=job.created,
            updated=job.updated,
            workflow_count=1,
            version=1,
        )
    )
    job.save()
    assert Job.get_saved(job.id).status == Status.FAILED.value


class _FailOnInProgressAndFailedStore(InMemoryJobStore):
    def put(self, record: JobRecord) -> None:
        if record.status in (Status.IN_PROGRESS.value, Status.FAILED.value):
            raise RuntimeError("run-and-fail-persist-failed")
        super().put(record)


@pytest.mark.asyncio
async def test_run_and_fail_persist_both_fail_restores_pre_run():
    set_job_store(_FailOnInProgressAndFailedStore())
    executed = []

    def work(task, context):
        executed.append(task.name)
        return "ok"

    job = _job_with_workflow(work)
    job.save()
    assert job.status == Status.SCHEDULED.value
    chan = Channel()
    await chan.send(job)

    with pytest.raises(RuntimeError, match="run-and-fail-persist-failed"):
        await Worker(chan).run_once()

    assert executed == []
    assert job._fsm.current().value == Status.SCHEDULED
    assert job.status == Status.SCHEDULED.value
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.SCHEDULED.value


@pytest.mark.asyncio
async def test_invalid_run_transition_does_not_execute_workflows():
    from pypepper.exceptions import InternalException

    executed = []

    def work(task, context):
        executed.append(task.name)
        return "ok"

    job = _job_with_workflow(work)
    # Leave job Scheduled in store/FSM but force FSM to Completed so RUN is invalid.
    job.apply_event(events.RUN)
    job.apply_event(events.COMPLETE)
    chan = Channel()
    await chan.send(job)

    with pytest.raises(InternalException):
        await Worker(chan).run_once()

    assert executed == []


def test_dispatch_save_failure_rolls_back_for_retry():
    set_job_store(_AlwaysFailStore())
    job = Job(category="x", channel_id="dispatch-rollback")

    with pytest.raises(RuntimeError, match="always-fail"):
        job.scheduled()

    assert job._fsm.current().value == Status.UNKNOWN
    assert job.status == Status.UNKNOWN.value
    assert Job.get_saved(job.id) is None

    reset_job_store()
    job.scheduled()
    assert Job.get_saved(job.id) is not None
    assert Job.get_saved(job.id).status == Status.SCHEDULED.value
    assert job.status == Status.SCHEDULED.value


def test_sql_missing_connection_raises_value_error():
    from pypepper.scheduler.store.mongodb import MongoJobStore
    from pypepper.scheduler.store.sql import SqlJobStore

    with pytest.raises(ValueError, match="postgres job store requires"):
        SqlJobStore(backend="postgres", host="localhost")
    with pytest.raises(ValueError, match="mysql job store requires"):
        SqlJobStore(backend="mysql", host="localhost")
    with pytest.raises(ValueError, match="mongodb job store requires"):
        MongoJobStore(host="localhost")


def test_setup_from_config_memory_preserves_existing_store():
    from types import SimpleNamespace

    from pypepper.scheduler.store import setup_from_config

    store = get_job_store()
    store.put(
        JobRecord(
            id="keep-me",
            category="c",
            channel_id="ch",
            status=Status.SCHEDULED.value,
            created="t0",
            updated="t0",
        )
    )
    setup_from_config(SimpleNamespace(scheduler=SimpleNamespace(jobStore=SimpleNamespace(backend="memory"))))
    assert get_job_store() is store
    assert get_job_store().get("keep-me") is not None


def test_save_failure_does_not_mutate_job_fields():
    set_job_store(_AlwaysFailStore())
    job = Job(category="x", channel_id="ch")
    assert job._fsm.on(events.INIT).error is None
    assert job._fsm.on(events.SCHEDULE).error is None
    before_status = job.status
    before_updated = job.updated

    with pytest.raises(RuntimeError, match="always-fail"):
        job.save()

    assert job.status == before_status
    assert job.updated == before_updated
    assert Job.get_saved(job.id) is None


def test_to_record_uses_fsm_status():
    job = Job(category="x", channel_id="ch")
    assert job.status == Status.UNKNOWN.value
    assert job._fsm.on(events.INIT).error is None
    assert job._fsm.on(events.SCHEDULE).error is None
    # FSM advanced; durable Job.status not updated until save succeeds.
    assert job.status == Status.UNKNOWN.value
    assert job.to_record().status == Status.SCHEDULED.value


def test_channel_full_rolls_back_and_deletes_scheduled():
    import asyncio

    from pypepper.scheduler.channel import manager
    from pypepper.scheduler.job import ChannelFullError

    channel_id = "bounded-full"
    bounded = Channel(maxsize=1)
    assert asyncio.run(bounded.send("occupier")) is True
    manager.put(channel_id, bounded)
    try:
        job = Job(category="x", channel_id=channel_id)
        with pytest.raises(ChannelFullError, match="channel full"):
            job.scheduled()

        assert job._fsm.current().value == Status.UNKNOWN
        assert job.status == Status.UNKNOWN.value
        assert Job.get_saved(job.id) is None
    finally:
        manager.remove(channel_id)


class _FailDeleteStore(InMemoryJobStore):
    def delete(self, job_id: str) -> None:
        raise RuntimeError("delete-failed")


def test_channel_full_delete_failure_still_raises_channel_full():
    import asyncio

    from pypepper.scheduler.channel import manager
    from pypepper.scheduler.job import ChannelFullError

    set_job_store(_FailDeleteStore())
    channel_id = "bounded-full-delete-fail"
    bounded = Channel(maxsize=1)
    assert asyncio.run(bounded.send("occupier")) is True
    manager.put(channel_id, bounded)
    try:
        job = Job(category="x", channel_id=channel_id)
        with pytest.raises(ChannelFullError, match="channel full"):
            job.scheduled()

        assert job._fsm.current().value == Status.UNKNOWN
        assert job.status == Status.UNKNOWN.value
        # Best-effort delete failed: Scheduled ghost may remain.
        ghost = Job.get_saved(job.id)
        assert ghost is not None
        assert ghost.status == Status.SCHEDULED.value
    finally:
        manager.remove(channel_id)


def test_channel_full_ghost_then_retry_upserts():
    """Ghost Scheduled row after failed cleanup must not block a later successful schedule."""
    import asyncio

    from pypepper.scheduler.channel import manager
    from pypepper.scheduler.job import ChannelFullError

    set_job_store(_FailDeleteStore())
    channel_id = "bounded-ghost-retry"
    bounded = Channel(maxsize=1)
    assert asyncio.run(bounded.send("occupier")) is True
    manager.put(channel_id, bounded)
    try:
        job = Job(category="x", channel_id=channel_id)
        with pytest.raises(ChannelFullError):
            job.scheduled()
        ghost = Job.get_saved(job.id)
        assert ghost is not None
        ghost_created = ghost.created

        assert asyncio.run(bounded.receive()) == "occupier"
        job.scheduled()
        saved = Job.get_saved(job.id)
        assert saved is not None
        assert saved.status == Status.SCHEDULED.value
        assert saved.created == ghost_created
        assert job._fsm.current().value == Status.SCHEDULED
        assert job.status == Status.SCHEDULED.value
    finally:
        manager.remove(channel_id)


def test_enqueue_failure_rolls_back_for_any_error(monkeypatch):
    from pypepper.scheduler.job import Processor

    def boom(self, job, chan, *, on_enqueued=None):
        raise RuntimeError("enqueue-boom")

    monkeypatch.setattr(Processor, "run", boom)
    job = Job(category="x", channel_id="enqueue-any-error")
    with pytest.raises(RuntimeError, match="enqueue-boom"):
        job.scheduled()

    assert job._fsm.current().value == Status.UNKNOWN
    assert job.status == Status.UNKNOWN.value
    assert Job.get_saved(job.id) is None


def test_post_enqueue_error_does_not_rollback(monkeypatch):
    import asyncio

    from pypepper.scheduler.channel import manager
    from pypepper.scheduler.job import Processor

    async def send_then_boom(job, chan, *, on_enqueued=None):
        ok = await chan.send(job)
        assert ok is True
        if on_enqueued is not None:
            on_enqueued()
        raise RuntimeError("after-send")

    monkeypatch.setattr(Processor, "async_run", staticmethod(send_then_boom))
    channel_id = "post-enqueue"
    chan = Channel()
    manager.put(channel_id, chan)
    try:
        job = Job(category="x", channel_id=channel_id)
        with pytest.raises(RuntimeError, match="after-send"):
            job.scheduled()

        assert job._fsm.current().value == Status.SCHEDULED
        assert job.status == Status.SCHEDULED.value
        assert Job.get_saved(job.id) is not None
        assert Job.get_saved(job.id).status == Status.SCHEDULED.value
        # Committed enqueue: job remains receivable on the channel.
        received = asyncio.run(chan.receive())
        assert received is job
    finally:
        manager.remove(channel_id)


def test_mongo_disconnect_benign_continues(monkeypatch):
    from pypepper.scheduler.store import mongodb as mongodb_mod

    connects: list[dict] = []

    def fake_disconnect(alias=None):
        raise RuntimeError(f"Connection with alias '{alias}' has not been created")

    def fake_connect(**kwargs):
        connects.append(kwargs)

    monkeypatch.setattr(mongodb_mod, "disconnect", fake_disconnect)
    monkeypatch.setattr(mongodb_mod, "mongo_connect", fake_connect)
    mongodb_mod.MongoJobStore(uri="mongodb://localhost/test", alias="benign-alias")
    assert connects and connects[0].get("alias") == "benign-alias"


def test_mongo_disconnect_non_benign_raises(monkeypatch):
    from pypepper.scheduler.store import mongodb as mongodb_mod

    def fake_disconnect(alias=None):
        raise RuntimeError("authentication failed during close")

    monkeypatch.setattr(mongodb_mod, "disconnect", fake_disconnect)
    monkeypatch.setattr(mongodb_mod, "mongo_connect", lambda **kwargs: None)
    with pytest.raises(RuntimeError, match="authentication failed"):
        mongodb_mod.MongoJobStore(uri="mongodb://localhost/test", alias="hard-fail-alias")


def test_channel_full_then_retry_succeeds():
    import asyncio

    from pypepper.scheduler.channel import manager
    from pypepper.scheduler.job import ChannelFullError

    channel_id = "bounded-retry"
    bounded = Channel(maxsize=1)
    assert asyncio.run(bounded.send("occupier")) is True
    manager.put(channel_id, bounded)
    try:
        job = Job(category="x", channel_id=channel_id)
        with pytest.raises(ChannelFullError):
            job.scheduled()
        assert job._fsm.current().value == Status.UNKNOWN
        assert Job.get_saved(job.id) is None

        assert asyncio.run(bounded.receive()) == "occupier"
        job.scheduled()
        assert job._fsm.current().value == Status.SCHEDULED
        assert Job.get_saved(job.id) is not None
        assert Job.get_saved(job.id).status == Status.SCHEDULED.value
    finally:
        manager.remove(channel_id)
