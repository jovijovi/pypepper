import json
import os
import socket
import sys
from string import Template
from typing import Any

from loguru import logger

from pedro.common.version import version

# Log format
log_fmt = "[<green>{time:YYYY-MM-DDTHH:mm:ss.SSSZ}</green>][<level>{level:<8}</level>][<cyan>$host:$user</cyan>]" \
          "[<cyan>pid:{process}|tid:{thread}</cyan>][<cyan>{file.path}:{line}</cyan>]" \
          "[<cyan>{module}.{function}</cyan>][<magenta>{extra[req_id]}</magenta>][<level>{message}</level>]"

# Template of log format
log_format_template = Template(log_fmt).substitute(host=socket.gethostname(), user=os.getlogin())

# Log default config
config = {
    "handlers": [
        {
            "sink": sys.stdout,

            # Log format
            "format": log_format_template,

            # Default log level
            "level": "TRACE",

            # Adds colors to logs
            "colorize": True,

            # Enqueue the messages to ensure logs integrity
            # Ref: https://loguru.readthedocs.io/en/stable/overview.html#asynchronous-thread-safe-multiprocess-safe
            "enqueue": True,
        },
    ],
    "levels": [
        dict(name="FATAL", no=60, icon="☠", color="<RED><bold>"),
    ],
    "extra": {
        # Default request ID
        "req_id": 0,
    },
}

logger.remove()
logger.configure(**config)


class Logger:
    def __init__(self):
        self._logger = logger.opt(depth=1)

    def get_logger(self):
        return self._logger

    def request_id(self, req_id=0):
        self._logger = self._logger.bind(req_id=req_id)
        return self

    def logo(self, msg: str):
        msg += json.dumps(version.get_version_info(), indent=4)
        self._logger.info(msg)

    # Severity: 5
    def trace(self, msg: str, *args: Any, **kwargs: Any):
        self._logger.trace(msg, *args, **kwargs)

    # Severity: 10
    def debug(self, msg: str, *args: Any, **kwargs: Any):
        self._logger.debug(msg, *args, **kwargs)

    # Severity: 20
    def info(self, msg: str, *args: Any, **kwargs: Any):
        self._logger.info(msg, *args, **kwargs)

    # Severity: 30
    def warn(self, msg: str, *args: Any, **kwargs: Any):
        self._logger.warning(msg, *args, **kwargs)

    # Severity: 40
    def error(self, msg: str, *args: Any, **kwargs: Any):
        self._logger.error(msg, *args, **kwargs)

    # Severity: 60
    def fatal(self, msg: str, *args: Any, **kwargs: Any):
        self._logger.log("FATAL", msg, *args, **kwargs)

    def close(self):
        self._logger.complete()
        self._logger.remove()


log = Logger()
