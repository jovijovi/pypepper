"""Validation and -O safety for helper.db connectors."""

import pytest

from pypepper.helper.db import mongodb, mysql, postgres


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


def test_mysql_ping_rejects_none_engine():
    with pytest.raises(ValueError, match="engine"):
        mysql.ping(None)  # type: ignore[arg-type]


def test_mongodb_connect_rejects_none_config():
    with pytest.raises(ValueError, match="database config"):
        mongodb.connect(None)  # type: ignore[arg-type]


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


def test_helper_valueerror_survives_optimize():
    """Missing discrete fields must raise ValueError even under PYTHONOPTIMIZE."""
    import subprocess
    import sys

    code = (
        "from pypepper.helper.db import postgres\n"
        "try:\n"
        "    postgres.connect(postgres.Config(username='u', password='p', host='h', db=None))\n"
        "except ValueError as e:\n"
        "    assert 'db' in str(e)\n"
        "    raise SystemExit(0)\n"
        "raise SystemExit('expected ValueError')\n"
    )
    result = subprocess.run(
        [sys.executable, "-O", "-c", code],
        capture_output=True,
        text=True,
        cwd=".",
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
