"""Sequential workflow runner over tasks."""

from __future__ import annotations

import time
from abc import ABCMeta
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import cast

from pypepper.common.log import log
from pypepper.scheduler.base import IBase
from pypepper.scheduler.task import Task

__all__ = ["IWorkflow", "Workflow"]


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
        - ``round_timeout`` seconds soft-timeout per execute attempt (0 = none). Timed-out
          work may keep running in a background thread; the next attempt can overlap.
        - ``retry_count`` / ``retry_delay`` / ``retry_until_completed`` / ``retry_until_max``:
          until+count0 uses per-round ``retry_until_max``; until+count>0 caps at count+1;
          until false uses count+1 as before.
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

        # Soft timeout: do not wait for the worker on shutdown so TimeoutError fails
        # fast and retries can proceed while orphaned work may still run.
        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(executor.execute, task, task.context)
        try:
            return cast(object | None, future.result(timeout=timeout))
        except FuturesTimeoutError as e:
            # On 3.10+, FuturesTimeoutError is TimeoutError. Only wrap wait timeouts;
            # if the worker already finished, re-raise its exception.
            if not future.done():
                raise TimeoutError(
                    f"Task execute exceeded round_timeout={timeout}s: id={task.id}, name={task.name}"
                ) from e
            worker_exc = future.exception()
            if worker_exc is not None:
                raise worker_exc from None
            raise
        finally:
            pool.shutdown(wait=False, cancel_futures=False)

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
