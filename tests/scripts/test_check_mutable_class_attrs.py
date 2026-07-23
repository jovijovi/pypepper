"""Unit tests for scripts/check_mutable_class_attrs.py AnnAssign coverage."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_mutable_class_attrs.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_mutable_class_attrs", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ann_assign_mutable_class_attr_is_detected(tmp_path, monkeypatch):
    checker = _load_checker()
    src = tmp_path / "fake_pkg"
    src.mkdir()
    (src / "mod.py").write_text(
        "from threading import Lock\n"
        "class Foo:\n"
        "    _store: dict = {}\n"
        "    _lock: Lock = Lock()\n"
        "    _plain = []\n"
    )
    monkeypatch.setattr(checker, "ROOT", src)
    tree = ast.parse((src / "mod.py").read_text(encoding="utf-8"))
    visitor = checker.Visitor(src / "mod.py")
    visitor.visit(tree)
    joined = "\n".join(visitor.errors)
    assert "Foo._store" in joined
    assert "Foo._lock" in joined
    assert "Foo._plain" in joined


def test_ann_assign_without_value_is_ignored(tmp_path, monkeypatch):
    checker = _load_checker()
    src = tmp_path / "fake_pkg"
    src.mkdir()
    (src / "mod.py").write_text("class Bar:\n    _hint: dict\n")
    monkeypatch.setattr(checker, "ROOT", src)
    tree = ast.parse((src / "mod.py").read_text(encoding="utf-8"))
    visitor = checker.Visitor(src / "mod.py")
    visitor.visit(tree)
    assert visitor.errors == []
