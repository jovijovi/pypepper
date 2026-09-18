"""Shared pytest fixtures: local devenv skip/fail and process-wide registry reset."""

from __future__ import annotations

import pytest

from pypepper.common.cache import Cache
from pypepper.common.config import config
from pypepper.common.tracing import shutdown as tracing_shutdown
from pypepper.loader import loader
from pypepper.network.http.sse.connection import connection_manager
from pypepper.network.http.sse.security import sse_security
from pypepper.scheduler.channel import manager as channel_manager
from pypepper.scheduler.job import dispatcher as job_dispatcher
from pypepper.scheduler.store import reset_job_store
from tests.support.devenv import DB_INFO, apply_db_constraint, tcp_port_open


def pytest_configure(config: pytest.Config) -> None:
    for mark, (name, _port) in DB_INFO.items():
        config.addinivalue_line("markers", f"{mark}: tests that need a local {name} instance")


@pytest.fixture(autouse=True)
def _skip_or_fail_when_db_unavailable(request: pytest.FixtureRequest) -> None:
    """Skip DB tests when the port is down locally; fail in CI if devenv is required."""
    apply_db_constraint(request.node.get_closest_marker)


@pytest.fixture
def tcp_port_open_fn():
    """TCP probe used by store tests (same helper as local devenv skip)."""
    return tcp_port_open


def _reset_job_store_for_tests() -> None:
    """Fresh memory store without carrying deferred durable YAML into the next test."""
    reset_job_store()
    # reset_job_store re-arms deferred from the last loaded YAML; clear for isolation.
    config.mark_scheduler_job_store_applied()


@pytest.fixture(autouse=True)
def _reset_global_registries():
    """Reset process-wide registries between tests to avoid cross-test pollution."""
    with connection_manager._lock:
        connection_manager._connections.clear()

    with channel_manager._lock:
        channel_manager._job_channel.clear()

    with job_dispatcher._lock:
        job_dispatcher._processors.clear()

    loader._module_loader_mapper.clear()

    _reset_job_store_for_tests()

    with sse_security._rate_limit_lock:
        sse_security._rate_limit_cache = Cache(maxsize=1000, ttl=60)

    tracing_shutdown()

    yield

    tracing_shutdown()

    _reset_job_store_for_tests()

    with connection_manager._lock:
        connection_manager._connections.clear()
    with channel_manager._lock:
        channel_manager._job_channel.clear()
    with job_dispatcher._lock:
        job_dispatcher._processors.clear()
    loader._module_loader_mapper.clear()
    with sse_security._rate_limit_lock:
        sse_security._rate_limit_cache = Cache(maxsize=1000, ttl=60)
