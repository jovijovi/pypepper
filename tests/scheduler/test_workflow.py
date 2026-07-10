import pytest

from pypepper.scheduler.executor import CallableExecutor, Executor
from pypepper.scheduler.task import Task
from pypepper.scheduler.workflow import Workflow


def test_workflow_runs_executors_in_order():
    executed = []

    def make_exec(name):
        def _run(task, context):
            executed.append(name)
            return name

        return CallableExecutor(_run)

    task_1 = Task(
        channel_id='channel_1',
        dag_id='dag_1',
        fingerprint='fingerprint_1',
        name='Test Task',
        category='Test Category',
        description='This is a test task',
        tags=[],
        executor=make_exec('t1'),
    )

    task_2 = Task(
        channel_id='channel_2',
        dag_id='dag_2',
        fingerprint='fingerprint_2',
        name='Another Test Task',
        category='Another Test Category',
        description='This is another test task',
        tags=[],
        executor=make_exec('t2'),
    )

    workflow = Workflow()
    assert workflow.run() == []

    workflow.add_task(task_1)
    workflow.add_tasks([task_2])
    tasks = workflow.get_tasks()

    assert len(tasks) == 2
    assert tasks[0] == task_1
    assert tasks[1] == task_2

    results = workflow.run()
    assert results == ['t1', 't2']
    assert executed == ['t1', 't2']


def test_workflow_optional_task_failure_continues():
    def boom(task, context):
        raise RuntimeError('boom')

    def ok(task, context):
        return 'ok'

    failing = Task(
        channel_id='c',
        dag_id='d',
        fingerprint='f',
        name='fail',
        category='c',
        description='',
        tags=[],
        executor=CallableExecutor(boom),
        optional=True,
    )
    succeeding = Task(
        channel_id='c',
        dag_id='d',
        fingerprint='f2',
        name='ok',
        category='c',
        description='',
        tags=[],
        executor=CallableExecutor(ok),
    )

    workflow = Workflow()
    workflow.add_tasks([failing, succeeding])
    assert workflow.run() == [None, 'ok']


def test_workflow_non_optional_failure_raises():
    def boom(task, context):
        raise RuntimeError('boom')

    task = Task(
        channel_id='c',
        dag_id='d',
        fingerprint='f',
        name='fail',
        category='c',
        description='',
        tags=[],
        executor=CallableExecutor(boom),
        optional=False,
    )
    workflow = Workflow()
    workflow.add_task(task)
    with pytest.raises(RuntimeError, match='boom'):
        workflow.run()


def test_noop_executor():
    task = Task(
        channel_id='c',
        dag_id='d',
        fingerprint='f',
        name='noop',
        category='c',
        description='',
        tags=[],
        executor=Executor(),
    )
    workflow = Workflow()
    workflow.add_task(task)
    assert workflow.run() == [None]
