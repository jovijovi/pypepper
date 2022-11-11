from typing import Callable, TypeVar, ParamSpec

from pedro.common.log import log
from pedro.common.utils import time
from pedro.common.utils.random import random
from pedro.exceptions import InternalException

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
    :param retry_times: retry times
    :param retry_interval: retry interval
    :param verbose_log: verbose log
    :return: function result
    """
    if not func:
        raise InternalException("invalid function")

    for i in range(retry_times):
        try:
            return func()
        except InternalException as e:
            if verbose_log:
                log.error('Try times={}, error={}', i + 1, e)

            if i + 1 == retry_times:
                raise e

            time.sleep(second=retry_interval)


def random_retry_interval(
        min_interval: int = DEFAULT_RETRY_MIN_INTERVAL,
        max_interval: int = DEFAULT_RETRY_MAX_INTERVAL,
) -> int:
    return random.rand_uint_between(min_interval, max_interval)
