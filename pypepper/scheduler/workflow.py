"""Sequential workflow runner over tasks."""

from __future__ import annotations

import time
from abc import ABCMeta
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from threading import Lock
from typing import cast

from pypepper.common.log import log
from pypepper.scheduler.base import IBase
from pypepper.scheduler.task import Task

__all__ = ["IWorkflow", "Workflow"]

# Cap concurrent soft-timeout orphan executes in-process. The work queue remains
# unbounded: further submits wait for a worker; short result(timeout=T) may fire
# before the task starts. Cross-job contention is possible under saturation.
_SOFT_TIMEOUT_MAX_WORKERS = 32
_pool_lock = Lock()
_soft_timeout_pool_ref: ThreadPoolExecutor | None = None


def _soft_timeout_pool() -> ThreadPoolExecutor:
    """Lazily create the shared soft-timeout executor (tests may replace the ref)."""
    global _soft_timeout_pool_ref
    if _soft_timeout_pool_ref is not None:
        return _soft_timeout_pool_ref
    with _pool_lock:
        if _soft_timeout_pool_ref is None:
            _soft_timeout_pool_ref = ThreadPoolExecutor(max_workers=_SOFT_TIMEOUT_MAX_WORKERS)
        return _soft_timeout_pool_ref


class IWorkflow(IBase, metaclass=ABCMeta):
    tasks: list[Task]


class Workflow(IWorkflow):
    def __init__(self) -> None:
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def add_tasks(self, tasks: list[Task]) -> None:
        self.tasks.extend(tasks)

    def get_tasks(self) -> list[Task]:
        return self.tasks

    def run(self) -> list[object]:
        """
        Sequentially execute tasks.

        Per task:
        - ``round_times`` outer rounds (default 1); each round has its own retry budget.
          Success returns early; later rounds run only after a full failed inner budget.
        - ``round_timeout`` seconds soft-timeout per execute attempt (0 = none). Timed-out
          work may keep running on the shared soft-timeout pool; the next attempt can
          overlap. Concurrent orphan executes are capped (``_SOFT_TIMEOUT_MAX_WORKERS``);
          further submits queue and a short timeout may fire before the task starts.
        - Retry modes: until false → ``retry_count + 1``; until + count 0 → per-round
          ``retry_until_max``; until + count > 0 → ``retry_count + 1`` (max ignored).
        - ``optional``: failed optional tasks continue the workflow.

        Non-optional task failure aborts the workflow.
        """
        from pypepper.common.tracing import get_tracer

        with get_tracer("pypepper.scheduler").start_as_current_span("scheduler.workflow.run"):
            if len(self.tasks) == 0:
                return []

            results: list[object] = []
            for task in self.tasks:
                result = self._run_task(task)
                results.append(result)
            return results

    @staticmethod
    def _attempts_per_round(task: Task) -> int:
        retry_count = int(task.retry_count or 0)
        if task.retry_until_completed and retry_count == 0:
            return max(1, int(task.retry_until_max))
        return max(1, retry_count + 1)

    @staticmethod
    def _execute_once(task: Task) -> object | None:
        executor = task.executor
        if executor is None:
            return None

        timeout = int(task.round_timeout or 0)
        if timeout <= 0:
            return cast(object | None, executor.execute(task, task.context))

        # Soft timeout via shared pool: do not shut down the pool so TimeoutError
        # fails fast and retries can proceed while orphaned work may still run.
        future: Future[object | None] = _soft_timeout_pool().submit(executor.execute, task, task.context)
        try:
            return cast(object | None, future.result(timeout=timeout))
        except FuturesTimeoutError as e:
            # On 3.10+, FuturesTimeoutError is TimeoutError. If the worker finished in
            # the race window, return/raise its outcome; otherwise wrap the wait timeout.
            if future.done():
                return cast(object | None, future.result())
            raise TimeoutError(f"Task execute exceeded round_timeout={timeout}s: id={task.id}, name={task.name}") from e

    def _run_task(self, task: Task) -> object | None:
        rounds = max(1, int(task.round_times or 1))
        attempts = self._attempts_per_round(task)
        last_error: Exception | None = None

        for round_idx in range(rounds):
            for attempt in range(attempts):
                try:
                    return self._execute_once(task)
                except Exception as e:
                    last_error = e
                    log.warn(
                        f"Task failed: id={task.id}, name={task.name}, "
                        f"round={round_idx + 1}/{rounds}, attempt={attempt + 1}/{attempts}, error={e}"
                    )
                    if attempt + 1 < attempts and task.retry_delay:
                        time.sleep(task.retry_delay)

        if task.optional:
            log.warn(f"Optional task failed, continuing: id={task.id}, error={last_error}")
            return None

        raise last_error if last_error else RuntimeError(f"Task failed: {task.id}")
