import json

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
