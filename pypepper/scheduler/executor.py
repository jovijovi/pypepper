"""Task executor interfaces, callable adapter, and named registry."""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from threading import Lock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pypepper.common.context import Context
    from pypepper.scheduler.task import Task

ExecutorFactory = Callable[[], "IExecutor"]


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

    def __init__(self, func: Callable[..., Any]) -> None:
        self._func = func

    def execute(self, task: Task, context: Context | None = None) -> Any:
        return self._func(task, context)


class ExecutorRegistry:
    """Explicit process-wide registry of named executor factories."""

    _instance: ExecutorRegistry | None = None
    _init_lock = Lock()
    _lock: Lock
    _factories: dict[str, ExecutorFactory | IExecutor]

    def __new__(cls) -> ExecutorRegistry:
        with cls._init_lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._lock = Lock()
                inst._factories = {}
                cls._instance = inst
            return cls._instance

    def register(self, name: str, factory: ExecutorFactory | IExecutor) -> None:
        if not name:
            raise ValueError("invalid executor id")
        if factory is None:
            raise ValueError("invalid executor factory")
        with self._lock:
            self._factories[name] = factory

    def resolve(self, name: str) -> IExecutor:
        if not name:
            raise ValueError("invalid executor id")
        with self._lock:
            spec = self._factories.get(name)
        if spec is None:
            raise ValueError(f"unknown executor_id: {name}")
        if isinstance(spec, IExecutor):
            return spec
        return spec()

    def clear(self) -> None:
        with self._lock:
            self._factories.clear()


executor_registry = ExecutorRegistry()
