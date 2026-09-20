"""Integration tests for DB-backed job stores (requires devenv)."""

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
from pypepper.scheduler.store.interfaces import IJobStore
from pypepper.scheduler.task import Task
from pypepper.scheduler.worker import Worker
from pypepper.scheduler.workflow import Workflow

POSTGRES_URI = "postgresql+psycopg://postgres:example@localhost:5432/mock_pypepper"
MYSQL_URI = "mysql+pymysql://root:example@localhost:3306/mock_pypepper?charset=utf8mb4"
MONGO_URI = "mongodb://test:test@localhost:27017/test"

_BACKENDS = (
    pytest.param("postgres", POSTGRES_URI, marks=pytest.mark.requires_postgres, id="postgres"),
    pytest.param("mysql", MYSQL_URI, marks=pytest.mark.requires_mysql, id="mysql"),
    pytest.param("mongodb", MONGO_URI, marks=pytest.mark.requires_mongodb, id="mongodb"),
)


@pytest.fixture(autouse=True)
def _reset_store():
    yield
    reset_job_store()


def _crud_roundtrip(backend: str, uri: str) -> None:
    store = configure_job_store(backend, uri=uri)
    record = JobRecord(
        id=f"db-{backend}-1",
        category="demo",
        channel_id=f"ch-{backend}",
        status=Status.SCHEDULED.value,
        created="t0",
        updated="t0",
        workflow_count=1,
        version=1,
    )
    store.clear()
    store.put(record)
    assert store.get(record.id) == record
    assert store.list(channel_id=record.channel_id) == [record]

    updated = JobRecord(
        id=record.id,
        category="demo2",
        channel_id=record.channel_id,
        status=Status.IN_PROGRESS.value,
        created="should-not-overwrite",
        updated="t1",
        workflow_count=2,
        version=2,
    )
    store.put(updated)
    got = store.get(record.id)
    assert got is not None
    assert got.category == "demo2"
    assert got.status == Status.IN_PROGRESS.value
    assert got.version == 2
    assert got.created == "t0"

    store.delete(record.id)
    assert store.get(record.id) is None


def _status_fence_roundtrip(backend: str, uri: str) -> None:
    store = configure_job_store(backend, uri=uri)
    job_id = f"db-fence-{backend}"
    store.clear()
    store.put(
        JobRecord(
            id=job_id,
            category="keep",
            channel_id="ch",
            status=Status.COMPLETED.value,
            created="t0",
            updated="t1",
            workflow_count=1,
            version=1,
        )
    )
    store.put(
        JobRecord(
            id=job_id,
            category="stale",
            channel_id="ch-stale",
            status=Status.SCHEDULED.value,
            created="should-not-overwrite",
            updated="t2",
            workflow_count=0,
            version=2,
        )
    )
    got = store.get(job_id)
    assert got is not None
    assert got.status == Status.COMPLETED.value
    assert got.category == "keep"
    assert got.channel_id == "ch"
    assert got.created == "t0"
    assert got.updated == "t1"
    assert got.workflow_count == 1
    store.delete(job_id)


@pytest.mark.requires_postgres
def test_postgres_crud():
    _crud_roundtrip("postgres", POSTGRES_URI)


@pytest.mark.requires_mysql
def test_mysql_crud():
    _crud_roundtrip("mysql", MYSQL_URI)


@pytest.mark.requires_mongodb
def test_mongodb_crud():
    _crud_roundtrip("mongodb", MONGO_URI)


@pytest.mark.requires_postgres
def test_postgres_put_does_not_downgrade_status():
    _status_fence_roundtrip("postgres", POSTGRES_URI)


@pytest.mark.requires_mysql
def test_mysql_put_does_not_downgrade_status():
    _status_fence_roundtrip("mysql", MYSQL_URI)


@pytest.mark.requires_mongodb
def test_mongodb_put_does_not_downgrade_status():
    _status_fence_roundtrip("mongodb", MONGO_URI)


@pytest.mark.requires_mongodb
def test_mongodb_concurrent_put_preserves_created():
    """Concurrent first inserts must keep a single stable ``created``."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    store = configure_job_store("mongodb", uri=MONGO_URI)
    store.clear()
    job_id = "mongo-concurrent-created"
    barrier = Barrier(2)

    def _put(created: str, updated: str) -> None:
        barrier.wait(timeout=5)
        store.put(
            JobRecord(
                id=job_id,
                category="c",
                channel_id="ch",
                status=Status.SCHEDULED.value,
                created=created,
                updated=updated,
                workflow_count=1,
                version=1,
            )
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_put, "t-a", "u1")
        f2 = pool.submit(_put, "t-b", "u2")
        f1.result()
        f2.result()

    got = store.get(job_id)
    assert got is not None
    assert got.created in ("t-a", "t-b")
    assert got.channel_id == "ch"
    # Later put must not rewrite created.
    store.put(
        JobRecord(
            id=job_id,
            category="c2",
            channel_id="ch",
            status=Status.IN_PROGRESS.value,
            created="should-not-overwrite",
            updated="u3",
            workflow_count=2,
            version=2,
        )
    )
    again = store.get(job_id)
    assert again is not None
    assert again.created == got.created
    store.delete(job_id)


async def _worker_lifecycle(backend: str, uri: str, channel_id: str) -> None:
    configure_job_store(backend, uri=uri)
    get_job_store().clear()

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
    job = Job(category=backend, channel_id=channel_id)
    job.workflows = [workflow]
    assert job._fsm.on(events.INIT).error is None
    assert job._fsm.on(events.SCHEDULE).error is None
    job.save()
    assert Job.get_saved(job.id) is not None
    assert Job.get_saved(job.id).status == Status.SCHEDULED.value

    chan = Channel()
    await chan.send(job)
    await Worker(chan).run_once()
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.COMPLETED.value


@pytest.mark.asyncio
@pytest.mark.requires_postgres
async def test_postgres_worker_lifecycle():
    await _worker_lifecycle("postgres", POSTGRES_URI, "pg-lifecycle")


@pytest.mark.asyncio
@pytest.mark.requires_mysql
async def test_mysql_worker_lifecycle():
    await _worker_lifecycle("mysql", MYSQL_URI, "mysql-lifecycle")


@pytest.mark.asyncio
@pytest.mark.requires_mongodb
async def test_mongodb_worker_lifecycle():
    await _worker_lifecycle("mongodb", MONGO_URI, "mongo-lifecycle")


class _FailPutProxy(IJobStore):
    def __init__(self, inner: IJobStore) -> None:
        self._inner = inner

    def put(self, record: JobRecord) -> None:
        raise RuntimeError("proxy-put-failed")

    def get(self, job_id: str) -> JobRecord | None:
        return self._inner.get(job_id)

    def delete(self, job_id: str) -> None:
        self._inner.delete(job_id)

    def list(self, channel_id: str | None = None) -> list[JobRecord]:
        return self._inner.list(channel_id)

    def clear(self) -> None:
        self._inner.clear()


@pytest.mark.parametrize(("backend", "uri"), _BACKENDS)
def test_db_scheduled_put_failure_after_enqueue_keeps_job_on_channel(backend: str, uri: str):
    """save() after successful send must not roll back; store has no row."""
    import asyncio

    from pypepper.scheduler.channel import manager

    inner = configure_job_store(backend, uri=uri)
    inner.clear()
    set_job_store(_FailPutProxy(inner))
    channel_id = f"ch-fail-put-{backend}"
    manager.remove(channel_id)
    job = Job(category="x", channel_id=channel_id)
    try:
        with pytest.raises(RuntimeError, match="proxy-put-failed"):
            job.scheduled()
        assert job._fsm.current().value == Status.SCHEDULED
        assert job.status == Status.UNKNOWN.value
        assert inner.get(job.id) is None
        chan = manager.get(channel_id)
        assert chan is not None
        assert chan.length() == 1
        assert asyncio.run(chan.receive()) is job
    finally:
        manager.remove(channel_id)


@pytest.mark.parametrize(("backend", "uri"), _BACKENDS)
def test_db_enqueue_failure_writes_nothing(backend: str, uri: str):
    """Channel-full enqueue failure must not persist a Scheduled row."""
    import asyncio

    from pypepper.scheduler.channel import manager
    from pypepper.scheduler.job import ChannelFullError

    inner = configure_job_store(backend, uri=uri)
    inner.clear()
    set_job_store(inner)
    channel_id = f"db-full-{backend}"
    bounded = Channel(maxsize=1)
    assert asyncio.run(bounded.send("occupier")) is True
    manager.put(channel_id, bounded)
    try:
        job = Job(category="x", channel_id=channel_id)
        with pytest.raises(ChannelFullError, match="channel full"):
            job.scheduled()
        assert job._fsm.current().value == Status.UNKNOWN
        assert job.status == Status.UNKNOWN.value
        assert inner.get(job.id) is None
    finally:
        manager.remove(channel_id)
        inner.clear()
