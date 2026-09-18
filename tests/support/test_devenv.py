"""Unit tests for devenv TCP probes and skip/fail helpers."""

from __future__ import annotations

import socket

import pytest

from tests.support import devenv


class _Marker:
    pass


def test_tcp_port_open_false_for_closed_port():
    # Port 1 (tcpmux) is not used by devenv; avoids bind-close races on ephemeral ports.
    assert devenv.tcp_port_open("127.0.0.1", 1) is False


def test_tcp_port_open_true_for_listening_port():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = int(srv.getsockname()[1])
    try:
        assert devenv.tcp_port_open("127.0.0.1", port) is True
    finally:
        srv.close()


def test_db_unavailability_reason_none_when_ports_up(monkeypatch):
    monkeypatch.setitem(devenv.db_available, "requires_postgres", True)
    monkeypatch.setitem(devenv.db_available, "requires_mysql", True)
    monkeypatch.setitem(devenv.db_available, "requires_mongodb", True)

    def get_closest_marker(name: str):
        return _Marker() if name == "requires_postgres" else None

    assert devenv.db_unavailability_reason(get_closest_marker) is None


def test_db_unavailability_reason_when_marked_backend_down(monkeypatch):
    monkeypatch.setitem(devenv.db_available, "requires_postgres", False)

    def get_closest_marker(name: str):
        return _Marker() if name == "requires_postgres" else None

    reason = devenv.db_unavailability_reason(get_closest_marker)
    assert reason is not None
    assert "PostgreSQL" in reason
    assert "5432" in reason
    assert "devenv/ci.yaml" in reason
    assert "--wait" in reason


def test_db_unavailability_reason_ignores_unmarked_down_backend(monkeypatch):
    monkeypatch.setitem(devenv.db_available, "requires_mysql", False)

    def get_closest_marker(_name: str):
        return None

    assert devenv.db_unavailability_reason(get_closest_marker) is None


def test_devenv_required_env(monkeypatch):
    monkeypatch.delenv(devenv.REQUIRE_DEVENV_ENV, raising=False)
    assert devenv.devenv_required() is False
    monkeypatch.setenv(devenv.REQUIRE_DEVENV_ENV, "1")
    assert devenv.devenv_required() is True
    monkeypatch.setenv(devenv.REQUIRE_DEVENV_ENV, "true")
    assert devenv.devenv_required() is True
    monkeypatch.setenv(devenv.REQUIRE_DEVENV_ENV, "0")
    assert devenv.devenv_required() is False


def test_apply_db_constraint_skips_when_not_required(monkeypatch):
    monkeypatch.setitem(devenv.db_available, "requires_postgres", False)
    monkeypatch.setattr(devenv, "devenv_required", lambda: False)

    def get_closest_marker(name: str):
        return _Marker() if name == "requires_postgres" else None

    with pytest.raises(pytest.skip.Exception, match="PostgreSQL"):
        devenv.apply_db_constraint(get_closest_marker)


def test_apply_db_constraint_fails_when_devenv_required(monkeypatch):
    monkeypatch.setitem(devenv.db_available, "requires_postgres", False)
    monkeypatch.setattr(devenv, "devenv_required", lambda: True)

    def get_closest_marker(name: str):
        return _Marker() if name == "requires_postgres" else None

    with pytest.raises(pytest.fail.Exception, match="PostgreSQL"):
        devenv.apply_db_constraint(get_closest_marker)
