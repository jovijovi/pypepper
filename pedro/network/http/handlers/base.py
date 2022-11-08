import json

from pedro.common.log import log
from pedro.common.version import version


def health():
    log.request_id().debug("health")
    return json.dumps(version.get_version_info())


# TODO:
def metrics():
    log.request_id().debug("metric")
    return json.dumps(version.get_version_info())
