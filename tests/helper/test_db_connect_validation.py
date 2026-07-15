"""Validation and -O safety for helper.db connectors."""

import pytest

from pypepper.helper.db import mongodb, mysql, postgres
from pypepper.helper.db.uri import build_mysql_uri, build_postgres_uri


@pytest.mark.parametrize(
    ("mod", "kwargs", "match"),
    [
        (postgres, {"username": None, "password": "p", "host": "h", "db": "d"}, "username"),
        (postgres, {"username": "u", "password": None, "host": "h", "db": "d"}, "password"),
        (postgres, {"username": "u", "password": "p", "host": None, "db": "d"}, "host"),
        (postgres, {"username": "u", "password": "p", "host": "h", "db": None}, "db"),
        (mysql, {"username": None, "password": "p", "host": "h", "db": "d"}, "username"),
        (mysql, {"username": "u", "password": None, "host": "h", "db": "d"}, "password"),
        (mysql, {"username": "u", "password": "p", "host": None, "db": "d"}, "host"),
        (mysql, {"username": "u", "password": "p", "host": "h", "db": None}, "db"),
    ],
)
def test_connect_raises_value_error_for_missing_fields(mod, kwargs, match):
    with pytest.raises(ValueError, match=match):
        mod.connect(mod.Config(**kwargs))


def test_postgres_connect_rejects_none_config():
    with pytest.raises(ValueError, match="database config"):
        postgres.connect(None)  # type: ignore[arg-type]


def test_mysql_connect_rejects_none_config():
    with pytest.raises(ValueError, match="database config"):
        mysql.connect(None)  # type: ignore[arg-type]


def test_mysql_ping_rejects_none_engine():
    with pytest.raises(ValueError, match="engine"):
        mysql.ping(None)  # type: ignore[arg-type]


def test_postgres_ping_rejects_none_engine():
    with pytest.raises(ValueError, match="engine"):
        postgres.ping(None)  # type: ignore[arg-type]


def test_mongodb_connect_rejects_none_config():
    with pytest.raises(ValueError, match="database config"):
        mongodb.connect(None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("mod", "builder", "kwargs"),
    [
        (
            postgres,
            build_postgres_uri,
            {
                "username": "u@x",
                "password": "p#ass:w/ord",
                "host": "localhost",
                "port": 5432,
                "db": "app",
            },
        ),
        (
            mysql,
            build_mysql_uri,
            {
                "username": "u:ser",
                "password": "p@ss/word",
                "host": "127.0.0.1",
                "port": 3306,
                "db": "app",
                "charset": "utf8mb4",
            },
        ),
    ],
)
def test_connect_passes_quoted_uri_to_create_engine(monkeypatch, mod, builder, kwargs):
    captured: list[str] = []

    class _FakeEngine:
        def connect(self):
            return "conn"

    def fake_create_engine(uri, *args, **kw):
        captured.append(uri)
        return _FakeEngine()

    monkeypatch.setattr(mod, "create_engine", fake_create_engine)
    assert mod.connect(mod.Config(**kwargs)) == "conn"
    assert captured == [builder(**kwargs)]


def test_public_reexports():
    from pypepper.common.config import config
    from pypepper.common.log import log
    from pypepper.event import Event, new
    from pypepper.fsm import FSM, State
    from pypepper.helper import mysql as helper_mysql
    from pypepper.network.http.sse import require_sse_api_key
    from pypepper.scheduler import Job, Status, setup_from_config

    assert config is not None
    assert log is not None
    assert Job is not None
    assert Status.UNKNOWN.value == "Unknown"
    assert callable(setup_from_config)
    assert FSM is not None
    assert State is not None
    assert Event is not None
    assert callable(new)
    assert helper_mysql is not None
    assert callable(require_sse_api_key)


@pytest.mark.parametrize("driver", ["postgres", "mysql"])
def test_helper_valueerror_survives_optimize(driver: str):
    """Missing discrete fields must raise ValueError even under PYTHONOPTIMIZE."""
    import subprocess
    import sys

    code = (
        f"from pypepper.helper.db import {driver}\n"
        f"try:\n"
        f"    {driver}.connect({driver}.Config(username='u', password='p', host='h', db=None))\n"
        f"except ValueError as e:\n"
        f"    assert 'db' in str(e)\n"
        f"    raise SystemExit(0)\n"
        f"raise SystemExit('expected ValueError')\n"
    )
    result = subprocess.run(
        [sys.executable, "-O", "-c", code],
        capture_output=True,
        text=True,
        cwd=".",
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
