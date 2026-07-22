import asyncio

import pytest

from pypepper.scheduler import events
from pypepper.scheduler.channel import Channel
from pypepper.scheduler.executor import CallableExecutor
from pypepper.scheduler.job import Job
from pypepper.scheduler.status import Status
from pypepper.scheduler.task import Task
from pypepper.scheduler.worker import Worker
from pypepper.scheduler.workflow import Workflow


@pytest.mark.asyncio
async def test_worker_processes_job_workflows():
    executed = []

    def work(task, context):
        executed.append(task.name)
        return task.name

    workflow = Workflow()
    workflow.add_task(
        Task(
            channel_id='ch',
            dag_id='dag',
            fingerprint='fp',
            name='step1',
            category='c',
            description='',
            tags=[],
            executor=CallableExecutor(work),
        )
    )

    job = Job(category='test', channel_id='worker-test')
    job.workflows = [workflow]
    # Mimic dispatch lifecycle before enqueue
    assert job._fsm.on(events.INIT).error is None
    assert job._fsm.on(events.SCHEDULE).error is None

    chan = Channel()
    await chan.send(job)

    worker = Worker(chan)
    processed = await worker.run_once()

    assert processed is job
    assert executed == ['step1']
    assert job._fsm.current().value == Status.COMPLETED


def _make_job(channel_id: str, name: str, work) -> Job:
    workflow = Workflow()
    workflow.add_task(
        Task(
            channel_id='ch',
            dag_id='dag',
            fingerprint=f'fp-{name}',
            name=name,
            category='c',
            description='',
            tags=[],
            executor=CallableExecutor(work),
        )
    )
    job = Job(category='test', channel_id=channel_id)
    job.workflows = [workflow]
    assert job._fsm.on(events.INIT).error is None
    assert job._fsm.on(events.SCHEDULE).error is None
    return job


@pytest.mark.asyncio
async def test_run_forever_continues_after_job_failure():
    executed = []
    good_done = asyncio.Event()

    def fail(task, context):
        raise RuntimeError("boom")

    def ok(task, context):
        executed.append(task.name)
        good_done.set()
        return task.name

    chan = Channel()
    await chan.send(_make_job('forever-fail', 'bad', fail))
    await chan.send(_make_job('forever-fail', 'good', ok))

    worker = Worker(chan)
    forever = asyncio.create_task(worker.run_forever())
    await asyncio.wait_for(good_done.wait(), timeout=5.0)
    assert executed == ['good']
    chan.request_stop()
    await asyncio.wait_for(forever, timeout=2.0)


@pytest.mark.asyncio
async def test_request_stop_unblocks_empty_receive():
    chan = Channel()
    worker = Worker(chan)

    async def stop_soon():
        await asyncio.sleep(0.05)
        chan.request_stop()

    stop_task = asyncio.create_task(stop_soon())
    await asyncio.wait_for(worker.run_forever(), timeout=2.0)
    await stop_task
    assert chan.stop is True


@pytest.mark.asyncio
async def test_request_stop_does_not_steal_bounded_capacity():
    """Regression: stop must not fill the only free slot on a bounded channel."""
    chan = Channel(maxsize=1)
    assert await chan.send("occupier") is True
    assert await chan.receive() == "occupier"
    assert chan.length() == 0
    chan.request_stop()
    assert chan.length() == 0
    # send refuses because stopped (not because queue full)
    assert await chan.send("after-stop") is False
    assert chan.length() == 0


@pytest.mark.asyncio
async def test_request_stop_abandons_queued_jobs():
    chan = Channel()
    await chan.send("left-behind")
    chan.request_stop()
    worker = Worker(chan)
    assert await worker.run_once() is None
    assert chan.length() == 1


@pytest.mark.asyncio
async def test_direct_receive_drains_after_stop_when_queued():
    """When stop is already set, direct receive() deterministically drains via get_nowait."""
    chan = Channel()
    await chan.send("queued")
    chan.request_stop()
    assert await Worker(chan).run_once() is None
    assert chan.length() == 1
    assert await chan.receive() == "queued"
    assert chan.length() == 0


@pytest.mark.asyncio
async def test_stop_assignment_wakes_blocked_receive():
    """Assigning Channel.stop = True uses the same wake path as request_stop()."""
    chan = Channel()
    worker = Worker(chan)

    async def stop_soon():
        await asyncio.sleep(0.05)
        chan.stop = True

    stop_task = asyncio.create_task(stop_soon())
    await asyncio.wait_for(worker.run_forever(), timeout=2.0)
    await stop_task
    assert chan.stop is True


def test_scheduled_raises_channel_stopped_error_and_rolls_back():
    from pypepper.scheduler.channel import manager
    from pypepper.scheduler.job import ChannelEnqueueError, ChannelFullError, ChannelStoppedError, Job

    chan = Channel()
    chan.request_stop()
    channel_id = "stopped-enqueue"
    manager.put(channel_id, chan)
    try:
        job = Job(category="x", channel_id=channel_id)
        with pytest.raises(ChannelStoppedError, match="channel stopped"):
            job.scheduled()
        assert job._fsm.current().value == Status.UNKNOWN
        assert job.status == Status.UNKNOWN.value
        assert Job.get_saved(job.id) is None

        # Subclass remains catchable as ChannelFullError / ChannelEnqueueError.
        job2 = Job(category="x", channel_id=channel_id)
        with pytest.raises(ChannelFullError, match="channel stopped"):
            job2.scheduled()
        job3 = Job(category="x", channel_id=channel_id)
        with pytest.raises(ChannelEnqueueError, match="channel stopped"):
            job3.scheduled()
        assert Job.get_saved(job2.id) is None
        assert Job.get_saved(job3.id) is None
    finally:
        manager.remove(channel_id)


@pytest.mark.asyncio
async def test_run_forever_reenqueues_after_run_persist_restore(monkeypatch):
    """RUN persist + FAIL persist both fail → restore + re-enqueue; continue picks it up."""
    executed = []
    good_done = asyncio.Event()
    save_calls = {"n": 0}

    def boom_then_ok(task, context):
        executed.append(task.name)
        good_done.set()
        return task.name

    chan = Channel()
    job = _make_job("reenqueue", "retry-me", boom_then_ok)
    await chan.send(job)

    original_save = Job.save

    def flaky_save(self):
        save_calls["n"] += 1
        # First save is RUN; second is FAIL preferred path — both fail once, then succeed.
        if save_calls["n"] <= 2:
            raise RuntimeError(f"persist-fail-{save_calls['n']}")
        return original_save(self)

    monkeypatch.setattr(Job, "save", flaky_save)

    worker = Worker(chan)
    forever = asyncio.create_task(worker.run_forever())
    await asyncio.wait_for(good_done.wait(), timeout=5.0)
    assert executed == ["retry-me"]
    chan.request_stop()
    await asyncio.wait_for(forever, timeout=2.0)


@pytest.mark.asyncio
async def test_run_forever_raises_job_redelivery_when_reenqueue_full(monkeypatch):
    from pypepper.scheduler.job import JobRedeliveryError

    chan = Channel(maxsize=1)
    job = _make_job("orphan", "stuck", lambda t, c: None)
    await chan.send(job)

    original_save = Job.save
    saves = {"n": 0}

    def flaky_save(self):
        saves["n"] += 1
        if saves["n"] <= 2:
            raise RuntimeError("persist-fail")
        return original_save(self)

    monkeypatch.setattr(Job, "save", flaky_save)

    real_send = Channel.send

    async def send_full_after_restore(self, value):
        # After restore, refuse re-enqueue (simulate full) while stop is false.
        if isinstance(value, Job) and saves["n"] >= 2:
            return False
        return await real_send(self, value)

    monkeypatch.setattr(Channel, "send", send_full_after_restore)

    worker = Worker(chan)
    with pytest.raises(JobRedeliveryError, match="could not re-enqueue"):
        await worker.run_forever()
