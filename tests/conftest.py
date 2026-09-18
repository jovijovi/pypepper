from __future__ import annotations

import socket

import pytest

from pypepper.common.cache import Cache
from pypepper.common.config import config
from pypepper.common.tracing import shutdown as tracing_shutdown
from pypepper.loader import loader
from pypepper.network.http.sse.connection import connection_manager
from pypepper.network.http.sse.security import sse_security
from pypepper.scheduler.channel import manager as channel_manager
from pypepper.scheduler.store import reset_job_store

_DEVENV_HINT = "start services with: docker compose -f devenv/ci.yaml up -d"
_PROBE_TIMEOUT_S = 0.3


def tcp_port_open(host: str, port: int, timeout: float = _PROBE_TIMEOUT_S) -> bool:
    """Return True when a TCP connect to ``host:port`` succeeds within ``timeout``."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture
def tcp_port_open_fn():
    """Expose :func:`tcp_port_open` without importing ``conftest`` from tests."""
    return tcp_port_open


POSTGRES_AVAILABLE = tcp_port_open("127.0.0.1", 5432)
MYSQL_AVAILABLE = tcp_port_open("127.0.0.1", 3306)
MONGO_AVAILABLE = tcp_port_open("127.0.0.1", 27017)

_DB_MARKERS: dict[str, tuple[bool, str, int]] = {
    "requires_postgres": (POSTGRES_AVAILABLE, "PostgreSQL", 5432),
    "requires_mysql": (MYSQL_AVAILABLE, "MySQL", 3306),
    "requires_mongodb": (MONGO_AVAILABLE, "MongoDB", 27017),
}


@pytest.fixture(autouse=True)
def _skip_if_db_unavailable(request: pytest.FixtureRequest) -> None:
    """Skip tests marked for a local DB when that devenv port is down."""
    for mark, (up, name, port) in _DB_MARKERS.items():
        if request.node.get_closest_marker(mark) and not up:
            pytest.skip(f"{name} is not reachable on 127.0.0.1:{port}; {_DEVENV_HINT}")


def _reset_job_store_for_tests() -> None:
    """Fresh memory store without carrying deferred durable YAML into the next test."""
    reset_job_store()
    # reset_job_store re-arms deferred from the last loaded YAML; clear for isolation.
    config.mark_scheduler_job_store_applied()


@pytest.fixture(autouse=True)
def _reset_global_registries():
    """Reset process-wide registries between tests to avoid cross-test pollution."""
    # SSE connections
    with connection_manager._lock:
        connection_manager._connections.clear()

    # Channel manager
    with channel_manager._lock:
        channel_manager._job_channel.clear()

    # Loader registry
    loader._module_loader_mapper.clear()

    # Scheduler job store
    _reset_job_store_for_tests()

    # SSE rate-limit cache (process singleton)
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
    loader._module_loader_mapper.clear()
    with sse_security._rate_limit_lock:
        sse_security._rate_limit_cache = Cache(maxsize=1000, ttl=60)
