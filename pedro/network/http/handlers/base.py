from flask import request

from pedro.common.log import log
from pedro.common.version import version
from pedro.network.http import response


def health():
    log.request_id().trace("Receive HealthCheck. URL.Path={}", request.path)
    return response.build_response(code="200", data=version.get_version_info(), msg="OK")


def ping():
    log.request_id().debug("pong")
    return "pong"


# TODO:
def metrics():
    log.request_id().info("Receive MetricsCheck. URL.Path={}", request.path)
    return response.build_response(code="200", data="metrics", msg="OK")
