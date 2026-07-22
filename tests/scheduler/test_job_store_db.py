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
    ("postgres", POSTGRES_URI),
    ("mysql", MYSQL_URI),
    ("mongodb", MONGO_URI),
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


def test_postgres_crud():
    _crud_roundtrip("postgres", POSTGRES_URI)


def test_mysql_crud():
    _crud_roundtrip("mysql", MYSQL_URI)


def test_mongodb_crud():
    _crud_roundtrip("mongodb", MONGO_URI)


def test_mongodb_concurrent_put_preserves_created():
    """Concurrent upserts must not overwrite the first ``created`` value."""
    from concurrent.futures import ThreadPoolExecutor

    store = configure_job_store("mongodb", uri=MONGO_URI)
    store.clear()
    job_id = "mongo-concurrent-created"

    def _put(created: str, updated: str) -> None:
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
    # Second writer must not rewrite created to the other value after both finish.
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
async def test_postgres_worker_lifecycle():
    await _worker_lifecycle("postgres", POSTGRES_URI, "pg-lifecycle")


@pytest.mark.asyncio
async def test_mysql_worker_lifecycle():
    await _worker_lifecycle("mysql", MYSQL_URI, "mysql-lifecycle")


@pytest.mark.asyncio
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


class _FailDeleteProxy(IJobStore):
    def __init__(self, inner: IJobStore) -> None:
        self._inner = inner

    def put(self, record: JobRecord) -> None:
        self._inner.put(record)

    def get(self, job_id: str) -> JobRecord | None:
        return self._inner.get(job_id)

    def delete(self, job_id: str) -> None:
        raise RuntimeError("proxy-delete-failed")

    def list(self, channel_id: str | None = None) -> list[JobRecord]:
        return self._inner.list(channel_id)

    def clear(self) -> None:
        self._inner.clear()


@pytest.mark.parametrize(("backend", "uri"), _BACKENDS)
def test_db_scheduled_put_failure_rolls_back(backend: str, uri: str):
    """Schedule-path put failure must not leave a durable row or advanced lifecycle."""
    inner = configure_job_store(backend, uri=uri)
    inner.clear()
    set_job_store(_FailPutProxy(inner))
    job = Job(category="x", channel_id=f"ch-fail-put-{backend}")
    with pytest.raises(RuntimeError, match="proxy-put-failed"):
        job.scheduled()
    assert job._fsm.current().value == Status.UNKNOWN
    assert job.status == Status.UNKNOWN.value
    assert inner.get(job.id) is None


@pytest.mark.parametrize(("backend", "uri"), _BACKENDS)
def test_db_enqueue_delete_failure_leaves_ghost(backend: str, uri: str):
    """Channel-full cleanup delete failure may leave a Scheduled ghost on the DB store."""
    import asyncio

    from pypepper.scheduler.channel import manager
    from pypepper.scheduler.job import ChannelFullError

    inner = configure_job_store(backend, uri=uri)
    inner.clear()
    set_job_store(_FailDeleteProxy(inner))
    channel_id = f"db-full-del-{backend}"
    bounded = Channel(maxsize=1)
    assert asyncio.run(bounded.send("occupier")) is True
    manager.put(channel_id, bounded)
    try:
        job = Job(category="x", channel_id=channel_id)
        with pytest.raises(ChannelFullError, match="channel full"):
            job.scheduled()
        assert job._fsm.current().value == Status.UNKNOWN
        assert job.status == Status.UNKNOWN.value
        ghost = inner.get(job.id)
        assert ghost is not None
        assert ghost.status == Status.SCHEDULED.value
    finally:
        manager.remove(channel_id)
        inner.clear()
