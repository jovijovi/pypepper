import time

import pytest

from pypepper.scheduler.executor import CallableExecutor, Executor
from pypepper.scheduler.task import Task
from pypepper.scheduler.workflow import Workflow


def _task(name: str, executor, **kwargs) -> Task:
    return Task(
        channel_id="c",
        dag_id="d",
        fingerprint=f"fp-{name}",
        name=name,
        category="c",
        description="",
        tags=[],
        executor=executor,
        **kwargs,
    )


def test_workflow_runs_executors_in_order():
    executed = []

    def make_exec(name):
        def _run(task, context):
            executed.append(name)
            return name

        return CallableExecutor(_run)

    task_1 = Task(
        channel_id="channel_1",
        dag_id="dag_1",
        fingerprint="fingerprint_1",
        name="Test Task",
        category="Test Category",
        description="This is a test task",
        tags=[],
        executor=make_exec("t1"),
    )

    task_2 = Task(
        channel_id="channel_2",
        dag_id="dag_2",
        fingerprint="fingerprint_2",
        name="Another Test Task",
        category="Another Test Category",
        description="This is another test task",
        tags=[],
        executor=make_exec("t2"),
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
    assert results == ["t1", "t2"]
    assert executed == ["t1", "t2"]


def test_workflow_optional_task_failure_continues():
    def boom(task, context):
        raise RuntimeError("boom")

    def ok(task, context):
        return "ok"

    failing = _task("fail", CallableExecutor(boom), optional=True)
    succeeding = _task("ok", CallableExecutor(ok))

    workflow = Workflow()
    workflow.add_tasks([failing, succeeding])
    assert workflow.run() == [None, "ok"]


def test_workflow_non_optional_failure_raises():
    def boom(task, context):
        raise RuntimeError("boom")

    task = _task("fail", CallableExecutor(boom), optional=False)
    workflow = Workflow()
    workflow.add_task(task)
    with pytest.raises(RuntimeError, match="boom"):
        workflow.run()


def test_noop_executor():
    task = _task("noop", Executor())
    workflow = Workflow()
    workflow.add_task(task)
    assert workflow.run() == [None]


def test_workflow_round_times_succeeds_on_later_round():
    calls = {"n": 0}

    def flaky(task, context):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError(f"fail-{calls['n']}")
        return "ok"

    task = _task("rounds", CallableExecutor(flaky), round_times=3, retry_count=0)
    workflow = Workflow()
    workflow.add_task(task)
    assert workflow.run() == ["ok"]
    assert calls["n"] == 3


def test_workflow_round_timeout_counts_as_failure_then_retry():
    calls = {"n": 0}

    def slow_then_fast(task, context):
        calls["n"] += 1
        if calls["n"] == 1:
            time.sleep(1.5)
            return "late"
        return "ok"

    task = _task(
        "timeout",
        CallableExecutor(slow_then_fast),
        round_timeout=1,
        retry_count=1,
        retry_delay=0,
    )
    workflow = Workflow()
    workflow.add_task(task)
    assert workflow.run() == ["ok"]
    assert calls["n"] == 2


def test_workflow_retry_until_completed_with_zero_count():
    calls = {"n": 0}

    def eventually(task, context):
        calls["n"] += 1
        if calls["n"] < 4:
            raise RuntimeError("not yet")
        return "done"

    task = _task(
        "until",
        CallableExecutor(eventually),
        retry_until_completed=True,
        retry_count=0,
        retry_until_max=10,
        retry_delay=0,
    )
    workflow = Workflow()
    workflow.add_task(task)
    assert workflow.run() == ["done"]
    assert calls["n"] == 4


def test_workflow_retry_until_with_count_caps_attempts():
    calls = {"n": 0}

    def always_fail(task, context):
        calls["n"] += 1
        raise RuntimeError("nope")

    task = _task(
        "until-cap",
        CallableExecutor(always_fail),
        retry_until_completed=True,
        retry_count=2,
        retry_until_max=100,
        retry_delay=0,
    )
    workflow = Workflow()
    workflow.add_task(task)
    with pytest.raises(RuntimeError, match="nope"):
        workflow.run()
    assert calls["n"] == 3


def test_workflow_retry_until_max_exhausted():
    calls = {"n": 0}

    def always_fail(task, context):
        calls["n"] += 1
        raise RuntimeError("nope")

    task = _task(
        "until-max",
        CallableExecutor(always_fail),
        retry_until_completed=True,
        retry_count=0,
        retry_until_max=5,
        retry_delay=0,
    )
    workflow = Workflow()
    workflow.add_task(task)
    with pytest.raises(RuntimeError, match="nope"):
        workflow.run()
    assert calls["n"] == 5


def test_task_rejects_invalid_retry_until_max():
    with pytest.raises(ValueError, match="retry_until_max"):
        _task("bad", Executor(), retry_until_max=0)


def test_task_rejects_invalid_round_times():
    with pytest.raises(ValueError, match="round_times"):
        _task("bad", Executor(), round_times=0)
