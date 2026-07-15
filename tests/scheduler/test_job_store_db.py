"""Integration tests for DB-backed job stores (requires devenv)."""

from __future__ import annotations

import pytest

from pypepper.scheduler import events
from pypepper.scheduler.channel import Channel
from pypepper.scheduler.executor import CallableExecutor
from pypepper.scheduler.job import Job
from pypepper.scheduler.status import Status
from pypepper.scheduler.store import JobRecord, configure_job_store, get_job_store, reset_job_store
from pypepper.scheduler.task import Task
from pypepper.scheduler.worker import Worker
from pypepper.scheduler.workflow import Workflow

POSTGRES_URI = "postgresql+psycopg://postgres:example@localhost:5432/mock_pypepper"
MYSQL_URI = "mysql+pymysql://root:example@localhost:3306/mock_pypepper?charset=utf8mb4"
MONGO_URI = "mongodb://test:test@localhost:27017/test"


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
        created="t0",
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

    store.delete(record.id)
    assert store.get(record.id) is None


def test_postgres_crud():
    _crud_roundtrip("postgres", POSTGRES_URI)


def test_mysql_crud():
    _crud_roundtrip("mysql", MYSQL_URI)


def test_mongodb_crud():
    _crud_roundtrip("mongodb", MONGO_URI)


@pytest.mark.asyncio
async def test_postgres_worker_lifecycle():
    configure_job_store("postgres", uri=POSTGRES_URI)
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
    job = Job(category="pg", channel_id="pg-lifecycle")
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
async def test_mongodb_worker_lifecycle():
    configure_job_store("mongodb", uri=MONGO_URI)
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
    job = Job(category="mongo", channel_id="mongo-lifecycle")
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
