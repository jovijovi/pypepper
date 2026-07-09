import pytest

from pypepper.network.http import server
from pypepper.network.http.interfaces import ITaskHandler


class _EmptyHandlers(ITaskHandler):
    def register_handlers(self, app):
        pass

    def use_middleware(self, app):
        pass


def test_run_with_tls_requires_cert_and_key(monkeypatch):
    class _Https:
        certFile = ''
        keyFile = ''
        caFile = ''
        mutualTLS = False

    class _Network:
        httpsServer = _Https()

    class _Cfg:
        network = _Network()

    monkeypatch.setattr(
        'pypepper.network.http.server.config.get_yml_config',
        lambda: _Cfg(),
    )

    with pytest.raises(ValueError, match='certFile/keyFile'):
        server.run_with_tls(443, _EmptyHandlers())


def test_run_with_tls_passes_ssl_args_to_uvicorn(monkeypatch):
    class _Https:
        certFile = '/tmp/cert.pem'
        keyFile = '/tmp/key.pem'
        caFile = '/tmp/ca.pem'
        mutualTLS = True

    class _Network:
        httpsServer = _Https()

    class _Cfg:
        network = _Network()

    monkeypatch.setattr(
        'pypepper.network.http.server.config.get_yml_config',
        lambda: _Cfg(),
    )

    captured = {}

    def fake_run(app, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(server.uvicorn, 'run', fake_run)
    monkeypatch.setattr(server.handlers, 'register_handlers', lambda *a, **k: None)
    monkeypatch.setattr(server.handlers, 'use_middleware', lambda *a, **k: None)

    server.run_with_tls(55650, _EmptyHandlers(), host='127.0.0.1')

    assert captured['ssl_certfile'] == '/tmp/cert.pem'
    assert captured['ssl_keyfile'] == '/tmp/key.pem'
    assert captured['ssl_ca_certs'] == '/tmp/ca.pem'
    assert captured['port'] == 55650
    assert captured['host'] == '127.0.0.1'
