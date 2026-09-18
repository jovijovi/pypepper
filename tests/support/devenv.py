"""Local devenv TCP probes used to skip (or fail) DB integration tests."""

from __future__ import annotations

import os
import socket
from collections.abc import Callable
from typing import Any

import pytest

DEVENV_HINT = "start services with: docker compose -f devenv/ci.yaml up -d --wait"
REQUIRE_DEVENV_ENV = "PYPEPPER_REQUIRE_DEVENV"
_REQUIRE_DEVENV_TRUTHY = frozenset({"1", "true", "yes", "on"})
_PROBE_TIMEOUT_S = 0.3

# Marker name -> (service label, TCP port). Availability is in ``db_available``.
DB_INFO: dict[str, tuple[str, int]] = {
    "requires_postgres": ("PostgreSQL", 5432),
    "requires_mysql": ("MySQL", 3306),
    "requires_mongodb": ("MongoDB", 27017),
}


def tcp_port_open(host: str, port: int, timeout: float = _PROBE_TIMEOUT_S) -> bool:
    """Return True when a TCP connect to ``host:port`` succeeds within ``timeout``."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def devenv_required() -> bool:
    """True when CI (or a local run) must fail instead of skipping missing DBs."""
    return os.environ.get(REQUIRE_DEVENV_ENV, "").strip().lower() in _REQUIRE_DEVENV_TRUTHY


def _probe_db_available() -> dict[str, bool]:
    return {mark: tcp_port_open("127.0.0.1", port) for mark, (_name, port) in DB_INFO.items()}


# Mutable so unit tests can patch a single backend without re-importing.
db_available: dict[str, bool] = _probe_db_available()


def db_unavailability_reason(get_closest_marker: Callable[[str], Any | None]) -> str | None:
    """Return a skip/fail message if a DB marker is present and that port is down."""
    for mark, (name, port) in DB_INFO.items():
        if get_closest_marker(mark) is not None and not db_available.get(mark, False):
            return f"{name} is not reachable on 127.0.0.1:{port}; {DEVENV_HINT}"
    return None


def apply_db_constraint(get_closest_marker: Callable[[str], Any | None]) -> None:
    """Skip locally when a required DB is down; ``pytest.fail`` if devenv is required."""
    reason = db_unavailability_reason(get_closest_marker)
    if reason is None:
        return
    if devenv_required():
        pytest.fail(reason)
    pytest.skip(reason)
