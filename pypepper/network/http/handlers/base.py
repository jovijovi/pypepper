import time

from fastapi import Request

from pypepper.common.log import log
from pypepper.common.version import version
from pypepper.network.http import response

_PROCESS_START = time.time()


async def health(request: Request):
    log.request_id().trace("Receive HealthCheck. URL.Path={}", request.url.path)
    return response.build_response(code="200", data=version.get_version_info(), msg="OK")


async def ping():
    log.request_id().debug("pong")
    return "pong"


async def metrics(request: Request):
    log.request_id().info("Receive MetricsCheck. URL.Path={}", request.url.path)
    data = {
        'uptime_seconds': round(time.time() - _PROCESS_START, 3),
        'version': version.get_version_info(),
    }
    try:
        from pypepper.network.http.sse.connection import connection_manager
        stats = connection_manager.get_stats()
        data['sse'] = {
            'total_connections': stats.get('total_connections', 0),
            'active_connections': stats.get('active_connections', 0),
            'total_dropped_events': stats.get('total_dropped_events', 0),
        }
    except Exception:
        pass
    return response.build_response(code="200", data=data, msg="OK")
