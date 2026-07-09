import pytest

from pypepper.common.cache import Cache
from pypepper.loader import loader
from pypepper.network.http.sse.connection import connection_manager
from pypepper.network.http.sse.security import SSESecurityManager
from pypepper.scheduler.channel import manager as channel_manager


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

    # SSE rate-limit cache
    SSESecurityManager._rate_limit_cache = Cache(maxsize=1000, ttl=60)

    yield

    with connection_manager._lock:
        connection_manager._connections.clear()
    with channel_manager._lock:
        channel_manager._job_channel.clear()
    loader._module_loader_mapper.clear()
    SSESecurityManager._rate_limit_cache = Cache(maxsize=1000, ttl=60)
