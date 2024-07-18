import getpass
import json
import socket
import sys
from enum import Enum
from string import Template
from typing import Any

from loguru import logger

from pypepper.common.version import version


class LogLevel(str, Enum):
    """
    Log level
    """

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"

    @classmethod
    def has_name(cls, name) -> bool:
        """
        Check if the name is in LogLevel
        :param name: log level name
        :return: result
        """

        return name in cls.__members__.keys()

    @classmethod
    def has_value(cls, value) -> bool:
        """
        Check if the value is in LogLevel
        :param value: log level value
        :return: result
        """

        return value in cls.__members__.values()


class LogLevelFilter:
    """
    Log level filter
    """

    def __init__(self, level):
        self.level = level

    def __call__(self, record):
        level_no = logger.level(self.level).no
        return record["level"].no >= level_no


# Default log filter
default_log_filter = LogLevelFilter(LogLevel.TRACE)

# Log format
log_fmt = "[<green>{time:YYYY-MM-DDTHH:mm:ss.SSSZ}</green>][<level>{level:<8}</level>][<cyan>$host:$user</cyan>]" \
          "[<cyan>pid:{process}|tid:{thread}</cyan>][<cyan>{file.path}:{line}</cyan>]" \
          "[<cyan>{module}.{function}</cyan>][<magenta>{extra[req_id]}</magenta>][<level>{message}</level>]"

# Template of log format
log_format_template = Template(log_fmt).substitute(host=socket.gethostname(), user=getpass.getuser())

# Log default config
config = {
    "handlers": [
        {
            "sink": sys.stdout,

            # Log format
            "format": log_format_template,

            # Default log level
            "level": LogLevel.TRACE,

            # Adds colors to logs
            "colorize": True,

            # Enqueue the messages to ensure logs integrity
            # Ref: https://loguru.readthedocs.io/en/stable/overview.html#asynchronous-thread-safe-multiprocess-safe
            "enqueue": True,

            # Default log filter
            "filter": default_log_filter,
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
        self._logger.log(LogLevel.FATAL, msg, *args, **kwargs)

    def close(self):
        self._logger.complete()
        self._logger.remove()

    @staticmethod
    def set_log_level(level: str):
        if LogLevel.has_value(level):
            default_log_filter.level = level

    @staticmethod
    def set_colorize(colorize=True):
        config["handlers"][0]["colorize"] = colorize
        logger.remove()
        logger.configure(handlers=config["handlers"])


log = Logger()
