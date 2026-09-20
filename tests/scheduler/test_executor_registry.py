"""Unit tests for the named ExecutorRegistry singleton."""

from __future__ import annotations

import pytest
from pypepper.scheduler.executor import CallableExecutor, ExecutorRegistry, executor_registry


@pytest.fixture(autouse=True)
def _clear_registry():
    executor_registry.clear()
    yield
    executor_registry.clear()


def test_executor_registry_is_process_wide_singleton():
    assert ExecutorRegistry() is executor_registry
    assert ExecutorRegistry() is ExecutorRegistry()


def test_register_rejects_empty_name_and_missing_factory():
    with pytest.raises(ValueError, match="invalid executor id"):
        executor_registry.register("", CallableExecutor(lambda t, c: None))
    with pytest.raises(ValueError, match="invalid executor factory"):
        executor_registry.register("named", None)  # type: ignore[arg-type]


def test_resolve_rejects_empty_and_unknown_ids():
    with pytest.raises(ValueError, match="invalid executor id"):
        executor_registry.resolve("")
    with pytest.raises(ValueError, match="unknown executor_id"):
        executor_registry.resolve("missing")


def test_resolve_calls_factory_callable():
    built: list[CallableExecutor] = []

    def factory() -> CallableExecutor:
        inst = CallableExecutor(lambda t, c: "from-factory")
        built.append(inst)
        return inst

    executor_registry.register("factory-exec", factory)
    resolved = executor_registry.resolve("factory-exec")
    assert resolved is built[0]
