"""Task executor interfaces and callable adapter."""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pypepper.common.context import Context
    from pypepper.scheduler.task import Task


class IExecutor(metaclass=ABCMeta):
    @abstractmethod
    def execute(self, task: Task, context: Context | None = None) -> Any:
        pass


class Executor(IExecutor):
    """No-op executor (placeholder for tasks without work)."""

    def execute(self, task: Task, context: Context | None = None) -> Any:
        return None


class CallableExecutor(Executor):
    """Executor that runs a provided callable."""

    def __init__(self, func: Callable[..., Any]):
        self._func = func

    def execute(self, task: Task, context: Context | None = None) -> Any:
        return self._func(task, context)
