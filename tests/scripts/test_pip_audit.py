"""Unit tests for scripts/pip_audit.py command construction."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "pip_audit.py"


def _load_pip_audit():
    spec = importlib.util.spec_from_file_location("pip_audit_script", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pip_audit_cmd_includes_requirements_and_ignores(tmp_path, monkeypatch):
    checker = _load_pip_audit()
    ignore = tmp_path / ".pip-audit-ignore.txt"
    ignore.write_text("# comment\nGHSA-test-ignore  # reason\n\n", encoding="utf-8")
    monkeypatch.setattr(checker, "IGNORE_FILE", ignore)
    req = tmp_path / "requirements.txt"
    req.write_text("fastapi==0.141.1\n", encoding="utf-8")
    cmd = checker._pip_audit_cmd(req)
    assert "-r" in cmd
    assert str(req) in cmd
    assert cmd[cmd.index("--ignore-vuln") + 1] == "GHSA-test-ignore"


def test_audit_lock_export_runs_uv_export_then_pip_audit(tmp_path, monkeypatch):
    checker = _load_pip_audit()
    lock = tmp_path / "uv.lock"
    lock.write_text("version = 1\n", encoding="utf-8")
    monkeypatch.setattr(checker, "UV_LOCK", lock)
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "_uv_bin", lambda: "uv")
    monkeypatch.setattr(checker, "_ignored_vulns", lambda: [])

    calls: list[list[str]] = []

    def fake_run(cmd, *, cwd=None, stdout=None):
        calls.append(list(cmd))
        return 0

    monkeypatch.setattr(checker, "_run", fake_run)
    assert checker._audit_lock_export() == 0
    assert calls[0][:3] == ["uv", "export", "--frozen"]
    assert "--all-groups" in calls[0]
    assert "-r" in calls[1]
    assert "--no-deps" in calls[1]


def test_uv_bin_missing_raises(monkeypatch):
    checker = _load_pip_audit()
    monkeypatch.setattr(checker.shutil, "which", lambda _name: None)
    with pytest.raises(FileNotFoundError, match="uv is required"):
        checker._uv_bin()
