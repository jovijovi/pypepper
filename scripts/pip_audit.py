#!/usr/bin/env python3
"""Run pip-audit on requirements.txt and the locked uv.lock graph.

Honors ``.pip-audit-ignore.txt`` for both passes. The lock export is audited
with ``--no-deps --disable-pip`` (no re-resolution). Environment markers are
stripped so the host's Python/OS does not drop lock entries Dependabot still
sees (win32 / older-Python backports).
"""

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


def _pip_audit_cmd(requirements: Path, *, lock_graph: bool = False) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "pip_audit",
        "-S",
        "-r",
        str(requirements),
    ]
    if lock_graph:
        # Pre-resolved path: do not create a venv or re-resolve (needs --disable-pip).
        cmd.extend(["--no-deps", "--disable-pip"])
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
        "uv is required to audit the uv.lock graph (uv export --locked). "
        "Install uv from https://docs.astral.sh/uv/getting-started/installation/"
    )


def _strip_environment_markers(src: Path, dest: Path) -> None:
    """Write ``src`` with PEP 508 environment markers removed.

    pip-audit skips marker-false lines on the auditing host; Dependabot still
    flags those lock entries. Stripping markers audits the full name==version
    graph. ``--disable-pip`` rejects conflicting duplicate pins loudly.
    """
    out: list[str] = []
    for raw in src.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            out.append(raw)
            continue
        pkg, _sep, _marker = stripped.partition(";")
        out.append(pkg.rstrip())
    dest.write_text("\n".join(out) + "\n", encoding="utf-8")


def _audit_requirements() -> int:
    if not REQUIREMENTS.is_file():
        raise FileNotFoundError(f"missing requirements file: {REQUIREMENTS}")
    return _run(_pip_audit_cmd(REQUIREMENTS))


def _audit_lock_export() -> int:
    if not UV_LOCK.is_file():
        raise FileNotFoundError(f"missing lock file: {UV_LOCK}")
    uv = _uv_bin()
    with tempfile.TemporaryDirectory(prefix="pypepper-pip-audit-") as tmp:
        tmp_dir = Path(tmp)
        export_path = tmp_dir / "uv-export.txt"
        audit_path = tmp_dir / "uv-export-nomarker.txt"
        export_cmd = [
            uv,
            "export",
            "--locked",
            "--all-groups",
            "--no-hashes",
            "--no-emit-project",
            "-o",
            str(export_path),
        ]
        rc = _run(export_cmd, cwd=ROOT, stdout=subprocess.DEVNULL)
        if rc != 0:
            return rc
        _strip_environment_markers(export_path, audit_path)
        return _run(_pip_audit_cmd(audit_path, lock_graph=True))


def main() -> int:
    try:
        rc = _audit_requirements()
        if rc != 0:
            return rc
        return _audit_lock_export()
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
