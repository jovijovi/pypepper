"""Unit tests for scripts/check_devenv_healthy.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_devenv_healthy.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_devenv_healthy", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_ps_json_ndjson_and_array():
    checker = _load()
    ndjson = '{"Service":"mysql","State":"running","Health":"healthy"}\n{"Service":"mongo"}\n'
    rows = checker._parse_ps_json(ndjson)
    assert len(rows) == 2
    assert rows[0]["Service"] == "mysql"
    array = checker._parse_ps_json('[{"Service":"postgres","State":"running"}]')
    assert array[0]["Service"] == "postgres"
    assert checker._parse_ps_json("  ") == []


def test_check_services_reports_missing_and_unhealthy():
    checker = _load()
    rows = [
        {"Service": "mysql", "State": "running", "Health": "healthy"},
        {"Service": "mongo", "State": "running", "Health": "starting"},
    ]
    problems = checker.check_services(rows, tcp_open=lambda _host, _port: True)
    assert any("postgres: missing" in p for p in problems)
    assert any("mongo:" in p and "starting" in p for p in problems)
    assert not any(p.startswith("mysql:") for p in problems)


def test_check_services_ok_when_all_healthy():
    checker = _load()
    rows = [
        {"Service": "mysql", "State": "running", "Health": "healthy"},
        {"Service": "mongo", "State": "running", "Health": "healthy"},
        {"Service": "postgres", "State": "running", "Health": "healthy"},
    ]
    assert checker.check_services(rows, tcp_open=lambda _host, _port: False) == []


def test_check_services_empty_health_falls_back_to_tcp():
    checker = _load()
    rows = [
        {"Service": "mysql", "State": "running", "Health": ""},
        {"Service": "mongo", "State": "running"},
        {"Service": "postgres", "State": "running", "Health": ""},
    ]
    assert checker.check_services(rows, tcp_open=lambda _host, _port: True) == []
    problems = checker.check_services(rows, tcp_open=lambda _host, _port: False)
    assert len(problems) == 3
    assert all("127.0.0.1:" in p for p in problems)
