"""Run a snippet under ``python -O`` and require a ``ValueError``."""

from __future__ import annotations

import subprocess
import sys


def assert_valueerror_under_optimize(code: str, match: str) -> None:
    """``code`` must raise ``ValueError`` containing ``match`` even with ``-O``."""
    snippet = (
        "try:\n"
        f"    {code}\n"
        "except ValueError as e:\n"
        f"    assert {match!r} in str(e)\n"
        "    raise SystemExit(0)\n"
        "raise SystemExit('expected ValueError')\n"
    )
    result = subprocess.run(
        [sys.executable, "-O", "-c", snippet],
        capture_output=True,
        text=True,
        cwd=".",
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
