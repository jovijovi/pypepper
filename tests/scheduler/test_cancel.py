"""Job / Worker cancel path tests."""

from __future__ import annotations

import pytest

from pypepper.exceptions import InternalException
from pypepper.scheduler import events
from pypepper.scheduler.channel import Channel
from pypepper.scheduler.executor import CallableExecutor
from pypepper.scheduler.job import Job
from pypepper.scheduler.status import Status
from pypepper.scheduler.store import JobRecord, reset_job_store, set_job_store
from pypepper.scheduler.store.memory import InMemoryJobStore
from pypepper.scheduler.task import Task
from pypepper.scheduler.worker import Worker
from pypepper.scheduler.workflow import Workflow


@pytest.fixture(autouse=True)
def _fresh_job_store():
    reset_job_store()
    yield
    reset_job_store()


def _assert_cancelled(job: Job) -> None:
    assert job.is_cancelled()
    assert job._fsm.current().value == Status.CANCELLED
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.CANCELLED.value


def _workflow(work, *, name: str = "step1", channel_id: str = "cancel-ch") -> Workflow:
    workflow = Workflow()
    workflow.add_task(
        Task(
            channel_id=channel_id,
            dag_id="dag",
            fingerprint=f"fp-{name}",
            name=name,
            category="c",
            description="",
            tags=[],
            executor=CallableExecutor(work),
        )
    )
    return workflow


def _job_with_workflow(work, *, channel_id: str = "cancel-ch") -> Job:
    job = Job(category="test", channel_id=channel_id)
    job.workflows = [_workflow(work, channel_id=channel_id)]
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    return job


def test_cancel_from_scheduled_persists_cancelled():
    job = Job(category="test", channel_id="cancel-sched")
    job.scheduled()
    assert job._fsm.current().value == Status.SCHEDULED

    job.cancel()
    _assert_cancelled(job)


def test_cancel_from_in_progress_persists_cancelled():
    job = Job(category="test", channel_id="cancel-run")
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    job.apply_event(events.RUN)
    job.save()

    job.cancel()
    _assert_cancelled(job)


@pytest.mark.parametrize(
    "setup",
    [
        pytest.param(lambda j: None, id="unknown"),
        pytest.param(
            lambda j: (j.apply_event(events.INIT), None)[1],
            id="initializing",
        ),
        pytest.param(
            lambda j: (
                j.apply_event(events.INIT),
                j.apply_event(events.SCHEDULE),
                j.apply_event(events.RUN),
                j.apply_event(events.COMPLETE),
                j.save(),
            ),
            id="completed",
        ),
        pytest.param(
            lambda j: (
                j.apply_event(events.INIT),
                j.apply_event(events.SCHEDULE),
                j.apply_event(events.RUN),
                j.apply_event(events.FAIL),
                j.save(),
            ),
            id="failed",
        ),
        pytest.param(
            lambda j: (
                j.apply_event(events.INIT),
                j.apply_event(events.SCHEDULE),
                j.cancel(),
            ),
            id="already-cancelled",
        ),
    ],
)
def test_cancel_illegal_states_raise_without_dirty_write(setup):
    job = Job(category="test", channel_id="cancel-illegal")
    setup(job)
    before = Job.get_saved(job.id)
    before_status = before.status if before else None
    before_fsm = job._fsm.current().value if job._fsm.current() else None

    with pytest.raises(InternalException):
        job.cancel()

    assert (job._fsm.current().value if job._fsm.current() else None) == before_fsm
    after = Job.get_saved(job.id)
    after_status = after.status if after else None
    assert after_status == before_status


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


def test_cancel_save_failure_keeps_fsm_cancelled():
    class _FailCancelledStore(InMemoryJobStore):
        def put(self, record: JobRecord) -> None:
            if record.status == Status.CANCELLED.value:
                raise RuntimeError("cancel-persist-failed")
            super().put(record)

    set_job_store(_FailCancelledStore())
    job = Job(category="test", channel_id="cancel-save-fail")
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    job.save()

    with pytest.raises(RuntimeError, match="cancel-persist-failed"):
        job.cancel()

    assert job.is_cancelled()
    assert job._fsm.current().value == Status.CANCELLED
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.SCHEDULED.value


@pytest.mark.asyncio
async def test_worker_skips_already_cancelled_job():
    executed = []

    def work(task, context):
        executed.append(task.name)
        return "ok"

    job = _job_with_workflow(work)
    job.cancel()
    _assert_cancelled(job)

    chan = Channel()
    await chan.send(job)
    processed = await Worker(chan).run_once()

    assert processed is job
    assert executed == []
    _assert_cancelled(job)
    assert job.status != Status.IN_PROGRESS.value


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
    processed = await Worker(chan).run_once()

    assert processed is job
    _assert_cancelled(job)


@pytest.mark.asyncio
async def test_worker_skips_second_workflow_when_cancelled_between():
    executed = []
    hold = {"job": None}

    def work1(task, context):
        executed.append(task.name)
        hold["job"].cancel()
        return "ok"

    def work2(task, context):
        executed.append(task.name)
        return "ok"

    job = Job(category="test", channel_id="cancel-multi-wf")
    job.workflows = [
        _workflow(work1, name="wf1", channel_id="cancel-multi-wf"),
        _workflow(work2, name="wf2", channel_id="cancel-multi-wf"),
    ]
    hold["job"] = job
    job.apply_event(events.INIT)
    job.apply_event(events.SCHEDULE)
    job.save()

    chan = Channel()
    await chan.send(job)
    await Worker(chan).run_once()

    assert executed == ["wf1"]
    _assert_cancelled(job)


@pytest.mark.asyncio
async def test_worker_ignores_workflow_error_after_cancel():
    hold = {"job": None}

    def work(task, context):
        hold["job"].cancel()
        raise RuntimeError("workflow-boom")

    job = _job_with_workflow(work)
    hold["job"] = job
    job.save()

    chan = Channel()
    await chan.send(job)
    processed = await Worker(chan).run_once()

    assert processed is job
    _assert_cancelled(job)
    assert Job.get_saved(job.id).status != Status.FAILED.value


@pytest.mark.asyncio
async def test_worker_rethrows_when_cancel_persist_lags_after_workflow_error():
    class _FailCancelledStore(InMemoryJobStore):
        def put(self, record: JobRecord) -> None:
            if record.status == Status.CANCELLED.value:
                raise RuntimeError("cancel-persist-failed")
            super().put(record)

    set_job_store(_FailCancelledStore())
    hold = {"job": None}

    def work(task, context):
        with pytest.raises(RuntimeError, match="cancel-persist-failed"):
            hold["job"].cancel()
        # FSM already Cancelled; raise so Worker hits the except+cancelled path
        raise RuntimeError("workflow-boom")

    job = _job_with_workflow(work)
    hold["job"] = job
    job.save()

    chan = Channel()
    await chan.send(job)
    with pytest.raises(RuntimeError, match="cancel-persist-failed"):
        await Worker(chan).run_once()

    assert job.is_cancelled()
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.IN_PROGRESS.value


@pytest.mark.asyncio
async def test_worker_run_persist_fail_skips_restore_when_cancel_won():
    """RUN save fails while cancel already applied: keep Cancelled, do not restore Scheduled."""

    class _RaceStore(InMemoryJobStore):
        job: Job | None = None

        def put(self, record: JobRecord) -> None:
            if record.status == Status.IN_PROGRESS.value:
                assert self.job is not None
                # Concurrent cancel wins after RUN applied in memory.
                self.job.apply_event(events.CANCEL)
                raise RuntimeError("run-persist-failed")
            if record.status == Status.FAILED.value:
                raise RuntimeError("fail-persist-failed")
            super().put(record)

    store = _RaceStore()
    set_job_store(store)
    executed = []

    def work(task, context):
        executed.append(task.name)
        return "ok"

    job = _job_with_workflow(work, channel_id="cancel-run-race")
    store.job = job
    job.save()

    chan = Channel()
    await chan.send(job)
    with pytest.raises(RuntimeError, match="run-persist-failed"):
        await Worker(chan).run_once()

    assert executed == []
    assert job.is_cancelled()
    assert job._fsm.current().value == Status.CANCELLED
    # Must not have been restored to Scheduled.
    assert job.status != Status.SCHEDULED.value
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.CANCELLED.value


@pytest.mark.asyncio
async def test_channel_stop_does_not_cancel_queued_job():
    executed = []

    def work(task, context):
        executed.append(task.name)
        return "ok"

    job = _job_with_workflow(work, channel_id="stop-vs-cancel")
    job.save()

    chan = Channel()
    await chan.send(job)
    chan.stop = True
    worker = Worker(chan)
    assert await worker.run_once() is None

    assert job._fsm.current().value == Status.SCHEDULED
    assert not job.is_cancelled()
    assert executed == []
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.SCHEDULED.value
