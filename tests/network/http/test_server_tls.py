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
        certFile = ""
        keyFile = ""
        caFile = ""
        mutualTLS = False

    class _Network:
        httpsServer = _Https()

    class _Cfg:
        network = _Network()

    monkeypatch.setattr(
        "pypepper.network.http.server.config.get_yml_config",
        lambda: _Cfg(),
    )

    with pytest.raises(ValueError, match="certFile/keyFile"):
        server.run_with_tls(443, _EmptyHandlers())


def test_run_with_tls_passes_ssl_args_to_uvicorn(monkeypatch):
    import ssl

    class _Https:
        certFile = "/tmp/cert.pem"
        keyFile = "/tmp/key.pem"
        caFile = "/tmp/ca.pem"
        mutualTLS = True

    class _Network:
        httpsServer = _Https()

    class _Cfg:
        network = _Network()

    monkeypatch.setattr(
        "pypepper.network.http.server.config.get_yml_config",
        lambda: _Cfg(),
    )

    captured = {}

    def fake_run(application, **kwargs):
        captured["app"] = application
        captured.update(kwargs)

    monkeypatch.setattr(server.uvicorn, "run", fake_run)

    server.run_with_tls(55650, _EmptyHandlers(), host="127.0.0.1")

    assert captured["app"] is not server.app
    assert captured["ssl_certfile"] == "/tmp/cert.pem"
    assert captured["ssl_keyfile"] == "/tmp/key.pem"
    assert captured["ssl_ca_certs"] == "/tmp/ca.pem"
    assert captured["ssl_cert_reqs"] == ssl.CERT_REQUIRED
    assert captured["port"] == 55650
    assert captured["host"] == "127.0.0.1"


def test_run_with_tls_requires_ca_when_mutual_tls(monkeypatch):
    class _Https:
        certFile = "/tmp/cert.pem"
        keyFile = "/tmp/key.pem"
        caFile = ""
        mutualTLS = True

    class _Network:
        httpsServer = _Https()

    class _Cfg:
        network = _Network()

    monkeypatch.setattr(
        "pypepper.network.http.server.config.get_yml_config",
        lambda: _Cfg(),
    )

    with pytest.raises(ValueError, match="caFile"):
        server.run_with_tls(443, _EmptyHandlers())


def test_run_requires_http_or_https_enabled(monkeypatch):
    class _Server:
        enable = False
        port = 80

    class _Network:
        ip = "127.0.0.1"
        httpServer = _Server()
        httpsServer = _Server()

    class _Cfg:
        network = _Network()

    monkeypatch.setattr(
        "pypepper.network.http.server.config.get_yml_config",
        lambda: _Cfg(),
    )

    with pytest.raises(RuntimeError, match="Neither httpServer nor httpsServer"):
        server.run()


def test_run_raises_when_http_and_https_enabled(monkeypatch):
    class _Server:
        enable = True
        port = 80

    class _Network:
        ip = "127.0.0.1"
        httpServer = _Server()
        httpsServer = _Server()

    class _Cfg:
        network = _Network()

    monkeypatch.setattr(
        "pypepper.network.http.server.config.get_yml_config",
        lambda: _Cfg(),
    )

    with pytest.raises(RuntimeError, match="Both httpServer and httpsServer"):
        server.run()


def test_run_uses_http_when_enabled(monkeypatch):
    class _Http:
        enable = True
        port = 18080

    class _Https:
        enable = False
        port = 443

    class _Network:
        ip = "127.0.0.1"
        httpServer = _Http()
        httpsServer = _Https()

    class _Cfg:
        network = _Network()

    monkeypatch.setattr(
        "pypepper.network.http.server.config.get_yml_config",
        lambda: _Cfg(),
    )
    captured: dict = {}

    def fake_run(application, **kwargs):
        captured["app"] = application
        captured.update(kwargs)

    monkeypatch.setattr(server.uvicorn, "run", fake_run)
    server.run(_EmptyHandlers())
    assert captured["port"] == 18080
    assert captured["host"] == "127.0.0.1"
    assert "ssl_certfile" not in captured
    assert captured["app"] is not server.app


def test_run_with_tls_omits_ca_when_mutual_tls_false(monkeypatch):
    class _Https:
        certFile = "/tmp/cert.pem"
        keyFile = "/tmp/key.pem"
        caFile = "/tmp/ca.pem"
        mutualTLS = False

    class _Network:
        httpsServer = _Https()

    class _Cfg:
        network = _Network()

    monkeypatch.setattr(
        "pypepper.network.http.server.config.get_yml_config",
        lambda: _Cfg(),
    )

    captured = {}

    def fake_run(application, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(server.uvicorn, "run", fake_run)

    server.run_with_tls(55651, _EmptyHandlers(), host="127.0.0.1")

    assert "ssl_ca_certs" not in captured
    assert "ssl_cert_reqs" not in captured
    assert captured["ssl_certfile"] == "/tmp/cert.pem"
