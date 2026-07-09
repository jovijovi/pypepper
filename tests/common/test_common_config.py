import pytest

from pypepper.common.config import config


def test_load_config():
    config.load_config('./conf/app.config.yaml')
    result = config.get_yml_config()
    assert result is not None
    assert result.network.httpServer.port == 55550
    assert result.log.level == 'TRACE'
    assert result.sse.maxTotalConnections == 100
    assert list(result.sse.authentication.validKeys) == []
