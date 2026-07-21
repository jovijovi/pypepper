import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from unittest.mock import patch

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


def test_task_rejects_negative_round_timeout():
    with pytest.raises(ValueError, match="round_timeout"):
        _task("bad", Executor(), round_timeout=-1)


def test_task_rejects_negative_retry_delay():
    with pytest.raises(ValueError, match="retry_delay"):
        _task("bad", Executor(), retry_delay=-1)


def test_task_rejects_negative_retry_count():
    with pytest.raises(ValueError, match="retry_count"):
        _task("bad", Executor(), retry_count=-1)


def test_workflow_classic_retry_count_and_delay(monkeypatch):
    calls = {"n": 0}
    delays: list[float] = []

    def flaky(task, context):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError(f"fail-{calls['n']}")
        return "ok"

    def track_sleep(seconds):
        delays.append(seconds)

    monkeypatch.setattr(time, "sleep", track_sleep)

    task = _task(
        "classic",
        CallableExecutor(flaky),
        retry_count=2,
        retry_delay=7,
        retry_until_completed=False,
    )
    workflow = Workflow()
    workflow.add_task(task)
    assert workflow.run() == ["ok"]
    assert calls["n"] == 3
    assert delays == [7, 7]


def test_workflow_classic_retry_exhausted():
    calls = {"n": 0}

    def always_fail(task, context):
        calls["n"] += 1
        raise RuntimeError("nope")

    task = _task(
        "classic-exhausted",
        CallableExecutor(always_fail),
        retry_count=2,
        retry_delay=0,
        retry_until_completed=False,
    )
    workflow = Workflow()
    workflow.add_task(task)
    with pytest.raises(RuntimeError, match="nope"):
        workflow.run()
    assert calls["n"] == 3


def test_workflow_round_times_resets_retry_budget():
    calls = {"n": 0}

    def fail_then_ok(task, context):
        calls["n"] += 1
        # Round 1: fail both attempts; round 2 first attempt succeeds.
        if calls["n"] < 3:
            raise RuntimeError(f"fail-{calls['n']}")
        return "ok"

    task = _task(
        "budget-reset",
        CallableExecutor(fail_then_ok),
        round_times=2,
        retry_count=1,
        retry_delay=0,
    )
    workflow = Workflow()
    workflow.add_task(task)
    assert workflow.run() == ["ok"]
    assert calls["n"] == 3


def test_workflow_all_rounds_exhausted():
    calls = {"n": 0}

    def always_fail(task, context):
        calls["n"] += 1
        raise RuntimeError("nope")

    task = _task(
        "rounds-exhausted",
        CallableExecutor(always_fail),
        round_times=2,
        retry_count=1,
        retry_delay=0,
    )
    workflow = Workflow()
    workflow.add_task(task)
    with pytest.raises(RuntimeError, match="nope"):
        workflow.run()
    assert calls["n"] == 4  # 2 rounds × (1+1) attempts


def test_workflow_round_timeout_hang_raises_within_budget():
    """Hung execute must surface TimeoutError without waiting for the pool thread."""
    release = threading.Event()
    entered = threading.Event()

    def hang(task, context):
        entered.set()
        release.wait(timeout=60)
        return "never"

    task = _task(
        "hang",
        CallableExecutor(hang),
        round_timeout=1,
        retry_count=0,
        retry_delay=0,
    )
    workflow = Workflow()
    workflow.add_task(task)
    started = time.monotonic()
    try:
        with pytest.raises(TimeoutError, match="execute still running"):
            workflow.run()
        elapsed = time.monotonic() - started
        assert elapsed < 5, f"soft timeout blocked too long: {elapsed:.2f}s"
        assert entered.wait(timeout=2), "execute never started"
    finally:
        release.set()


def test_workflow_soft_timeout_orphan_failure_is_logged():
    """Started orphans that fail after wait-timeout must log via done-callback."""
    release = threading.Event()
    entered = threading.Event()
    logged = threading.Event()

    def hang_then_fail(task, context):
        entered.set()
        release.wait(timeout=60)
        raise RuntimeError("orphan-boom")

    from pypepper.common.log import log as pepper_log

    real_warn = pepper_log.warn

    def warn_and_signal(msg, *args, **kwargs):
        real_warn(msg, *args, **kwargs)
        if "orphan execute failed" in str(msg) and "orphan-boom" in str(msg):
            logged.set()

    task = _task(
        "orphan-fail",
        CallableExecutor(hang_then_fail),
        round_timeout=1,
        retry_count=0,
        retry_delay=0,
    )
    workflow = Workflow()
    workflow.add_task(task)
    try:
        with patch("pypepper.scheduler.workflow.log.warn", side_effect=warn_and_signal):
            with pytest.raises(TimeoutError, match="execute still running"):
                workflow.run()
            assert entered.wait(timeout=2), "execute never started"
            release.set()
            assert logged.wait(timeout=5), "orphan failure was not logged"
    finally:
        release.set()


def test_workflow_soft_timeout_returns_result_when_future_finishes_in_race():
    """If wait times out but the future completed successfully, return the result."""

    class _RacePool:
        def submit(self, fn, *args, **kwargs):
            future = Future()
            future.set_result("ok")
            return future

    real_result = Future.result

    def result_raise_timeout_once(self, timeout=None):
        if timeout is not None:
            raise FuturesTimeoutError()
        return real_result(self, timeout=timeout)

    with (
        patch("pypepper.scheduler.workflow._soft_timeout_pool", return_value=_RacePool()),
        patch.object(Future, "result", result_raise_timeout_once),
    ):
        task = _task("race", CallableExecutor(lambda t, c: "unused"), round_timeout=1)
        workflow = Workflow()
        workflow.add_task(task)
        assert workflow.run() == ["ok"]


def test_soft_timeout_pool_is_reused():
    from pypepper.scheduler import workflow as wf

    pool = wf._soft_timeout_pool()
    assert pool is wf._soft_timeout_pool()
    assert pool._max_workers == wf._SOFT_TIMEOUT_MAX_WORKERS


def test_workflow_soft_timeout_cancels_queued_before_start():
    """Under a saturated pool, pre-start timeout cancels queued work (no late execute)."""
    release = threading.Event()
    occupied = threading.Event()
    entered_second = threading.Event()
    calls = {"second": 0}

    def occupy(task, context):
        occupied.set()
        release.wait(timeout=60)
        return "occupy-done"

    def second(task, context):
        calls["second"] += 1
        entered_second.set()
        return "second-done"

    tiny = ThreadPoolExecutor(max_workers=1)
    try:
        with patch("pypepper.scheduler.workflow._soft_timeout_pool", return_value=tiny):
            hang_task = _task("occupy", CallableExecutor(occupy), round_timeout=30, retry_count=0)
            hang_future = tiny.submit(hang_task.executor.execute, hang_task, hang_task.context)
            assert occupied.wait(timeout=2), "occupy never grabbed the pool thread"

            task = _task(
                "queued",
                CallableExecutor(second),
                round_timeout=1,
                retry_count=0,
                retry_delay=0,
            )
            workflow = Workflow()
            workflow.add_task(task)
            with pytest.raises(TimeoutError, match="timed out before start"):
                workflow.run()
            assert calls["second"] == 0
            assert not entered_second.is_set()
        release.set()
        hang_future.result(timeout=5)
        assert calls["second"] == 0
        assert not entered_second.is_set()
    finally:
        release.set()
        tiny.shutdown(wait=False, cancel_futures=True)


def test_workflow_without_round_timeout_does_not_use_pool():
    calls = {"execute": 0}

    class _CountingExecutor(Executor):
        def execute(self, task, context=None):
            calls["execute"] += 1
            return "sync"

    with patch("pypepper.scheduler.workflow._soft_timeout_pool") as pool_factory:
        task = _task("no-timeout", _CountingExecutor(), round_timeout=0)
        workflow = Workflow()
        workflow.add_task(task)
        assert workflow.run() == ["sync"]
        pool_factory.assert_not_called()
    assert calls["execute"] == 1


def test_workflow_executor_timeout_error_not_wrapped_as_round_timeout():
    def boom_timeout(task, context):
        raise TimeoutError("executor-own-timeout")

    task = _task(
        "exec-timeout",
        CallableExecutor(boom_timeout),
        round_timeout=5,
        retry_count=0,
    )
    workflow = Workflow()
    workflow.add_task(task)
    with pytest.raises(TimeoutError, match="executor-own-timeout"):
        workflow.run()


def test_workflow_retry_until_max_is_per_round_not_global():
    calls = {"n": 0}

    def fail_until_round2(task, context):
        calls["n"] += 1
        # Round 1: 2 failures; round 2 first succeeds → proves budget resets.
        if calls["n"] < 3:
            raise RuntimeError(f"fail-{calls['n']}")
        return "ok"

    task = _task(
        "until-per-round",
        CallableExecutor(fail_until_round2),
        round_times=2,
        retry_until_completed=True,
        retry_count=0,
        retry_until_max=2,
        retry_delay=0,
    )
    workflow = Workflow()
    workflow.add_task(task)
    assert workflow.run() == ["ok"]
    assert calls["n"] == 3
