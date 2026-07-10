import pytest

from pypepper.common.log import Logger, log


def test_request_id_does_not_mutate_global_logger():
    base = log.get_logger()
    bound = log.request_id('req-isolation')
    assert bound is not log
    assert log.get_logger() is base
    # Bound logger should still expose logging methods
    bound.info('isolated request log')


def test_set_log_level():
    log.set_log_level('INFO')
    from pypepper.common.log import default_log_filter
    assert default_log_filter.level == 'INFO'
    log.set_log_level('TRACE')
    assert default_log_filter.level == 'TRACE'


def test_logger_methods_callable():
    log.trace('TRACE')
    log.debug('DEBUG')
    log.info('INFO')
    log.warn('WARN')
    log.error('ERROR')
    assert isinstance(log, Logger)
