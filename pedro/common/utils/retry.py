from typing import Any

from pedro.common.log import log
from pedro.common.utils import time


def run(f, retry_times=3, retry_interval=3, verbose_log=True) -> Any:
    """
    Retry running the function m times with n seconds interval
    :param f: function
    :param retry_times: retry times
    :param retry_interval: retry interval
    :param verbose_log: verbose log
    :return: function result
    """
    for i in range(retry_times):
        try:
            return f()
        except Exception as e:
            if verbose_log:
                log.error('Try times={}, error={}', i + 1, e)

            if i + 1 == retry_times:
                raise e

            time.sleep(second=retry_interval)
