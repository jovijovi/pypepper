from fastapi import Request

from pypepper.common.log import log
from pypepper.common.version import version
from pypepper.network.http import response


async def health(request: Request):
    log.request_id().trace("Receive HealthCheck. URL.Path={}", request.url.path)
    return response.build_response(code="200", data=version.get_version_info(), msg="OK")


async def ping():
    log.request_id().debug("pong")
    return "pong"


# TODO:
async def metrics(request: Request):
    log.request_id().info("Receive MetricsCheck. URL.Path={}", request.url.path)
    return response.build_response(code="200", data="metrics", msg="OK")
