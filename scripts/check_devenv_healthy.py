#!/usr/bin/env python3
"""Fail if devenv/ci.yaml services are not all running and healthy."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPOSE = ROOT / "devenv" / "ci.yaml"
EXPECTED_SERVICES = ("mysql", "mongo", "postgres")
SERVICE_PORTS = {"mysql": 3306, "mongo": 27017, "postgres": 5432}
_UNHEALTHY = frozenset({"unhealthy", "starting"})


def tcp_port_open(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_ps_json(raw: str) -> list[dict]:
    text = raw.strip()
    if not text:
        return []
    if text.startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("compose ps JSON array expected")
        return data
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def check_services(
    rows: list[dict],
    expected: tuple[str, ...] = EXPECTED_SERVICES,
    tcp_open: Callable[[str, int], bool] = tcp_port_open,
) -> list[str]:
    """Return human-readable problems; empty means all expected services are usable.

    Prefer compose ``Health=healthy``. If Health is omitted (some compose versions),
    require ``State=running`` and a TCP connect on the devenv port.
    """
    by_service: dict[str, dict] = {}
    for row in rows:
        name = str(row.get("Service") or "")
        if name:
            by_service[name] = row

    problems: list[str] = []
    for svc in expected:
        row = by_service.get(svc)
        if row is None:
            problems.append(f"{svc}: missing from compose ps")
            continue
        state = str(row.get("State") or "").lower()
        health = str(row.get("Health") or "").lower()
        if state != "running":
            problems.append(f"{svc}: State={row.get('State')!r} Health={row.get('Health')!r}")
            continue
        if health == "healthy":
            continue
        if health in _UNHEALTHY:
            problems.append(f"{svc}: State={row.get('State')!r} Health={row.get('Health')!r}")
            continue
        port = SERVICE_PORTS[svc]
        if not tcp_open("127.0.0.1", port):
            problems.append(
                f"{svc}: State={row.get('State')!r} Health={row.get('Health')!r} "
                f"and 127.0.0.1:{port} closed"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-f",
        "--file",
        default=str(DEFAULT_COMPOSE),
        help="compose file (default: devenv/ci.yaml)",
    )
    args = parser.parse_args(argv)
    cmd = ["docker", "compose", "-f", args.file, "ps", "--format", "json"]
    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print("error: docker is required to check devenv health", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or exc.stdout or str(exc)).strip()
        print(f"error: {' '.join(cmd)} failed: {err}", file=sys.stderr)
        return 1

    try:
        rows = _parse_ps_json(proc.stdout)
        problems = check_services(rows)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"error: could not parse compose ps JSON: {exc}", file=sys.stderr)
        return 1

    if problems:
        print("devenv is not healthy:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"{len(EXPECTED_SERVICES)} devenv services running and healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
