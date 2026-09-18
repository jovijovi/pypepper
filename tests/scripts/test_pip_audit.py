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


def test_pip_audit_cmd_includes_requirements_strict_and_ignores(tmp_path, monkeypatch):
    checker = _load_pip_audit()
    ignore = tmp_path / ".pip-audit-ignore.txt"
    ignore.write_text("# comment\nGHSA-test-ignore  # reason\n\n", encoding="utf-8")
    monkeypatch.setattr(checker, "IGNORE_FILE", ignore)
    req = tmp_path / "requirements.txt"
    req.write_text("fastapi==0.141.1\n", encoding="utf-8")
    cmd = checker._pip_audit_cmd(req)
    assert "-S" in cmd
    assert "-r" in cmd
    assert str(req) in cmd
    assert "--no-deps" not in cmd
    assert "--disable-pip" not in cmd
    assert cmd[cmd.index("--ignore-vuln") + 1] == "GHSA-test-ignore"


def test_pip_audit_cmd_lock_graph_disables_pip_resolve(tmp_path):
    checker = _load_pip_audit()
    req = tmp_path / "lock.txt"
    req.write_text("starlette==1.6.0\n", encoding="utf-8")
    cmd = checker._pip_audit_cmd(req, lock_graph=True)
    assert "-S" in cmd
    assert "--no-deps" in cmd
    assert "--disable-pip" in cmd


def test_strip_environment_markers(tmp_path):
    checker = _load_pip_audit()
    src = tmp_path / "export.txt"
    dest = tmp_path / "stripped.txt"
    src.write_text(
        "tomli==2.4.0 ; python_full_version < '3.11'\n"
        "    # via coverage\n"
        "starlette==1.6.0\n",
        encoding="utf-8",
    )
    checker._strip_environment_markers(src, dest)
    text = dest.read_text(encoding="utf-8")
    assert "tomli==2.4.0\n" in text
    assert ";" not in text
    assert "# via coverage" in text
    assert "starlette==1.6.0" in text


def test_audit_lock_export_uses_locked_and_stripped_file(tmp_path, monkeypatch):
    checker = _load_pip_audit()
    lock = tmp_path / "uv.lock"
    lock.write_text("version = 1\n", encoding="utf-8")
    monkeypatch.setattr(checker, "UV_LOCK", lock)
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "_uv_bin", lambda: "uv")
    monkeypatch.setattr(checker, "_ignored_vulns", lambda: [])

    calls: list[list[str]] = []
    audited_text: dict[str, str] = {}

    def fake_run(cmd, *, cwd=None, stdout=None):
        calls.append(list(cmd))
        if cmd[0] == "uv":
            export_path = Path(cmd[cmd.index("-o") + 1])
            export_path.write_text(
                "exceptiongroup==1.3.1 ; python_full_version < '3.11'\n",
                encoding="utf-8",
            )
        else:
            audited_text["body"] = Path(cmd[cmd.index("-r") + 1]).read_text(encoding="utf-8")
        return 0

    monkeypatch.setattr(checker, "_run", fake_run)
    assert checker._audit_lock_export() == 0
    assert calls[0][:3] == ["uv", "export", "--locked"]
    assert "--all-groups" in calls[0]
    assert "--frozen" not in calls[0]
    audit_cmd = calls[1]
    assert "-S" in audit_cmd
    assert "--no-deps" in audit_cmd
    assert "--disable-pip" in audit_cmd
    assert audited_text["body"] == "exceptiongroup==1.3.1\n"


def test_uv_bin_missing_raises(monkeypatch):
    checker = _load_pip_audit()
    monkeypatch.setattr(checker.shutil, "which", lambda _name: None)
    with pytest.raises(FileNotFoundError, match="uv is required"):
        checker._uv_bin()


def test_main_missing_lock_returns_2(tmp_path, monkeypatch):
    checker = _load_pip_audit()
    monkeypatch.setattr(checker, "REQUIREMENTS", tmp_path / "requirements.txt")
    (tmp_path / "requirements.txt").write_text("fastapi==0.141.1\n", encoding="utf-8")
    monkeypatch.setattr(checker, "UV_LOCK", tmp_path / "missing.lock")
    monkeypatch.setattr(checker, "_audit_requirements", lambda: 0)
    assert checker.main() == 2
