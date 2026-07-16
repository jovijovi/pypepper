"""Job / Worker cancel path tests."""

from __future__ import annotations

import pytest

from pypepper.exceptions import InternalException
from pypepper.scheduler import events
from pypepper.scheduler.channel import Channel
from pypepper.scheduler.executor import CallableExecutor
from pypepper.scheduler.job import Job
from pypepper.scheduler.status import Status
from pypepper.scheduler.store import reset_job_store
from pypepper.scheduler.task import Task
from pypepper.scheduler.worker import Worker
from pypepper.scheduler.workflow import Workflow


@pytest.fixture(autouse=True)
def _fresh_job_store():
    reset_job_store()
    yield
    reset_job_store()


def _job_with_workflow(work, *, channel_id: str = "cancel-ch") -> Job:
    workflow = Workflow()
    workflow.add_task(
        Task(
            channel_id=channel_id,
            dag_id="dag",
            fingerprint="fp",
            name="step1",
            category="c",
            description="",
            tags=[],
            executor=CallableExecutor(work),
        )
    )
    job = Job(category="test", channel_id=channel_id)
    job.workflows = [workflow]
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    return job


def test_cancel_from_scheduled_persists_cancelled():
    job = Job(category="test", channel_id="cancel-sched")
    job.scheduled()
    assert job._fsm.current().value == Status.SCHEDULED

    job.cancel()

    assert job._fsm.current().value == Status.CANCELLED
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.CANCELLED.value


def test_cancel_from_in_progress_persists_cancelled():
    job = Job(category="test", channel_id="cancel-run")
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    job.apply_event(events.RUN)
    job.save()

    job.cancel()

    assert job._fsm.current().value == Status.CANCELLED
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.CANCELLED.value


def test_cancel_from_completed_raises_and_does_not_dirty_store():
    job = Job(category="test", channel_id="cancel-done")
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    job.apply_event(events.RUN)
    job.apply_event(events.COMPLETE)
    job.save()
    before = Job.get_saved(job.id)
    assert before is not None
    assert before.status == Status.COMPLETED.value

    with pytest.raises(InternalException):
        job.cancel()

    assert job._fsm.current().value == Status.COMPLETED
    after = Job.get_saved(job.id)
    assert after is not None
    assert after.status == Status.COMPLETED.value


def test_fsm_cancel_transition_from_scheduled_and_in_progress():
    machine = events.build_scheduler_fsm()
    assert machine.on(events.INIT).error is None
    assert machine.on(events.SCHEDULE).error is None
    assert machine.on(events.CANCEL).error is None
    assert machine.current().value == Status.CANCELLED

    machine2 = events.build_scheduler_fsm()
    assert machine2.on(events.INIT).error is None
    assert machine2.on(events.SCHEDULE).error is None
    assert machine2.on(events.RUN).error is None
    assert machine2.on(events.CANCEL).error is None
    assert machine2.current().value == Status.CANCELLED


@pytest.mark.asyncio
async def test_worker_skips_already_cancelled_job():
    executed = []

    def work(task, context):
        executed.append(task.name)
        return "ok"

    job = _job_with_workflow(work)
    job.cancel()
    assert job._fsm.current().value == Status.CANCELLED

    chan = Channel()
    await chan.send(job)
    processed = await Worker(chan).run_once()

    assert processed is job
    assert executed == []
    assert job._fsm.current().value == Status.CANCELLED
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.CANCELLED.value


@pytest.mark.asyncio
async def test_worker_does_not_complete_when_cancelled_mid_run():
    hold = {"cancel_job": None}

    def work(task, context):
        job = hold["cancel_job"]
        assert job is not None
        job.cancel()
        return "ok"

    job = _job_with_workflow(work)
    hold["cancel_job"] = job
    job.save()

    chan = Channel()
    await chan.send(job)
    await Worker(chan).run_once()

    assert job._fsm.current().value == Status.CANCELLED
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.CANCELLED.value


@pytest.mark.asyncio
async def test_channel_stop_does_not_cancel_job():
    executed = []

    def work(task, context):
        executed.append(task.name)
        return "ok"

    job = _job_with_workflow(work, channel_id="stop-vs-cancel")
    job.save()

    chan = Channel()
    chan.stop = True
    worker = Worker(chan)
    assert await worker.run_once() is None

    assert job._fsm.current().value == Status.SCHEDULED
    assert executed == []
