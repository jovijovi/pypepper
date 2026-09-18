#!/usr/bin/env python3
"""Run pip-audit on requirements.txt and the frozen uv.lock graph."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORE_FILE = ROOT / ".pip-audit-ignore.txt"
REQUIREMENTS = ROOT / "requirements.txt"
UV_LOCK = ROOT / "uv.lock"


def _ignored_vulns() -> list[str]:
    if not IGNORE_FILE.is_file():
        return []
    ids: list[str] = []
    for raw in IGNORE_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Allow trailing comments after the ID.
        vuln_id = line.split("#", 1)[0].strip().split()[0]
        if vuln_id:
            ids.append(vuln_id)
    return ids


def _pip_audit_cmd(requirements: Path, *, no_deps: bool = False) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "pip_audit",
        "-r",
        str(requirements),
    ]
    if no_deps:
        cmd.append("--no-deps")
    for vuln_id in _ignored_vulns():
        cmd.extend(["--ignore-vuln", vuln_id])
    return cmd


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    stdout: int | None = None,
) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=cwd, stdout=stdout)


def _uv_bin() -> str:
    uv = shutil.which("uv")
    if uv:
        return uv
    raise FileNotFoundError(
        "uv is required to audit the uv.lock graph (uv export --frozen). "
        "Install uv from https://docs.astral.sh/uv/getting-started/installation/"
    )


def _audit_requirements() -> int:
    return _run(_pip_audit_cmd(REQUIREMENTS))


def _audit_lock_export() -> int:
    if not UV_LOCK.is_file():
        raise FileNotFoundError(f"missing lock file: {UV_LOCK}")
    uv = _uv_bin()
    with tempfile.TemporaryDirectory(prefix="pypepper-pip-audit-") as tmp:
        export_path = Path(tmp) / "uv-export.txt"
        export_cmd = [
            uv,
            "export",
            "--frozen",
            "--all-groups",
            "--no-hashes",
            "--no-emit-project",
            "-o",
            str(export_path),
        ]
        rc = _run(export_cmd, cwd=ROOT, stdout=subprocess.DEVNULL)
        if rc != 0:
            return rc
        # Export is the complete frozen graph; do not re-resolve.
        return _run(_pip_audit_cmd(export_path, no_deps=True))


def main() -> int:
    rc = _audit_requirements()
    if rc != 0:
        return rc
    return _audit_lock_export()


if __name__ == "__main__":
    raise SystemExit(main())
