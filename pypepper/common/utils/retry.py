from collections.abc import Callable
from typing import ParamSpec, TypeVar

from pypepper.common.log import log
from pypepper.common.utils import time
from pypepper.common.utils.random import random
from pypepper.exceptions import InternalException

DEFAULT_RETRY_TIMES: int = 3
DEFAULT_RETRY_INTERVAL: int = 3
DEFAULT_RETRY_MIN_INTERVAL: int = DEFAULT_RETRY_INTERVAL
DEFAULT_RETRY_MAX_INTERVAL: int = DEFAULT_RETRY_MIN_INTERVAL * 3

T = TypeVar("T")
P = ParamSpec("P")


def run(
    func: Callable[P, T],
    retry_times: int = DEFAULT_RETRY_TIMES,
    retry_interval: int = DEFAULT_RETRY_INTERVAL,
    verbose_log: bool = True,
) -> T:
    """
    Retry running the function m times with n seconds interval
    :param func: function
    :param retry_times: retry times, should be greater than 0
    :param retry_interval: retry interval, should be greater than or equal to 0
    :param verbose_log: verbose log
    :return: function result
    """
    if func is None:
        raise InternalException("invalid function")

    if retry_times <= 0:
        raise InternalException("invalid retry times")

    if retry_interval < 0:
        raise InternalException("invalid retry interval")

    last_error: Exception | None = None
    for i in range(retry_times):
        try:
            return func()  # type: ignore[call-arg]
        except Exception as e:
            last_error = e
            if verbose_log:
                log.error("Try times={}, error={}", i + 1, e)

            if i + 1 == retry_times:
                raise InternalException(e) from e

            time.sleep(second=retry_interval)

    raise InternalException(last_error) from last_error


def random_retry_interval(
    min_interval: int = DEFAULT_RETRY_MIN_INTERVAL,
    max_interval: int = DEFAULT_RETRY_MAX_INTERVAL,
) -> int:
    return random.rand_uint_between(min_interval, max_interval)
