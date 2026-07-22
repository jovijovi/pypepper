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
