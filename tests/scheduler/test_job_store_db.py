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
def test_db_put_failure_propagates(backend: str, uri: str):
    inner = configure_job_store(backend, uri=uri)
    inner.clear()
    set_job_store(_FailPutProxy(inner))
    record = JobRecord(
        id=f"fail-put-{backend}",
        category="x",
        channel_id=f"ch-{backend}",
        status=Status.SCHEDULED.value,
        created="t0",
        updated="t0",
    )
    with pytest.raises(RuntimeError, match="proxy-put-failed"):
        get_job_store().put(record)
    assert inner.get(record.id) is None


@pytest.mark.parametrize(("backend", "uri"), _BACKENDS)
def test_db_delete_failure_propagates(backend: str, uri: str):
    inner = configure_job_store(backend, uri=uri)
    inner.clear()
    record = JobRecord(
        id=f"fail-del-{backend}",
        category="x",
        channel_id=f"ch-{backend}",
        status=Status.SCHEDULED.value,
        created="t0",
        updated="t0",
    )
    inner.put(record)
    set_job_store(_FailDeleteProxy(inner))
    with pytest.raises(RuntimeError, match="proxy-delete-failed"):
        get_job_store().delete(record.id)
    assert inner.get(record.id) is not None
