from __future__ import annotations

import time
from abc import ABCMeta

from pypepper.common.log import log
from pypepper.scheduler.base import IBase
from pypepper.scheduler.task import Task


class IWorkflow(IBase, metaclass=ABCMeta):
    tasks: list[Task]


class Workflow(IWorkflow):
    def __init__(self):
        self.tasks: list[Task] = []

    def add_task(self, task: Task):
        self.tasks.append(task)

    def add_tasks(self, tasks: list[Task]):
        self.tasks.extend(tasks)

    def get_tasks(self) -> list[Task]:
        return self.tasks

    def run(self) -> list:
        """
        Sequentially execute tasks.
        Respects retry_count / retry_delay / optional.
        Non-optional task failure aborts the workflow.
        """
        from pypepper.common.tracing import get_tracer

        with get_tracer("pypepper.scheduler").start_as_current_span("scheduler.workflow.run"):
            if len(self.tasks) == 0:
                return []

            results = []
            for task in self.tasks:
                result = self._run_task(task)
                results.append(result)
            return results

    def _run_task(self, task: Task):
        attempts = max(1, int(task.retry_count or 0) + 1)
        last_error: Exception | None = None

        for attempt in range(attempts):
            try:
                executor = task.executor
                if executor is None:
                    return None
                return executor.execute(task, task.context)
            except Exception as e:
                last_error = e
                log.warn(f"Task failed: id={task.id}, name={task.name}, attempt={attempt + 1}/{attempts}, error={e}")
                if attempt + 1 < attempts and task.retry_delay:
                    time.sleep(task.retry_delay)

        if task.optional:
            log.warn(f"Optional task failed, continuing: id={task.id}, error={last_error}")
            return None

        raise last_error if last_error else RuntimeError(f"Task failed: {task.id}")
