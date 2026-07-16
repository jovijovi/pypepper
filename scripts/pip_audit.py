#!/usr/bin/env python3
"""Run pip-audit on requirements.txt, honoring .pip-audit-ignore.txt."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORE_FILE = ROOT / ".pip-audit-ignore.txt"
REQUIREMENTS = ROOT / "requirements.txt"


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


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pip_audit",
        "-r",
        str(REQUIREMENTS),
    ]
    for vuln_id in _ignored_vulns():
        cmd.extend(["--ignore-vuln", vuln_id])
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
