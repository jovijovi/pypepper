#!/usr/bin/env python3
"""Fail if pypepper classes declare mutable class-level instance state.

Detects patterns like:
  class Foo:
      _store = {}
      _lock = Lock()
      _annotated: dict = {}

Instance state must be initialized in __init__ / __new__.
Allowlisted intentional class constants are skipped.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'pypepper'

# Intentional shared class-level state (explicit singletons / class utilities)
ALLOWLIST_ATTRS: set[tuple[str, str, str]] = set()

# Allowed for singleton __new__ guards (not per-instance state)
ALLOWLIST_ATTR_NAMES = {'_init_lock', '_instance'}


MUTABLE_CALLS = {'Lock', 'RLock', 'dict', 'list', 'set', 'Cache'}


def _mutable_call_name(value: ast.expr) -> str | None:
    if not isinstance(value, ast.Call):
        return None
    func = value.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _is_mutable_value(value: ast.expr | None) -> bool:
    if value is None:
        return False
    if isinstance(value, (ast.Dict, ast.List, ast.Set)):
        return True
    if isinstance(value, ast.Call):
        name = _mutable_call_name(value)
        return name in MUTABLE_CALLS
    return False


def _should_flag_name(attr_name: str) -> bool:
    if attr_name == '__slots__':
        return False
    if not (attr_name.startswith('_') or attr_name == '__slots__'):
        return False
    if attr_name.isupper():
        return False
    if attr_name in ALLOWLIST_ATTR_NAMES:
        return False
    return True


class Visitor(ast.NodeVisitor):
    def __init__(self, path: Path):
        self.path = path
        self.errors: list[str] = []
        self._rel = str(path.relative_to(ROOT))

    def _report(self, node: ast.AST, class_name: str, attr_name: str) -> None:
        key = (self._rel, class_name, attr_name)
        if key in ALLOWLIST_ATTRS:
            return
        self.errors.append(
            f'{self._rel}:{node.lineno}: class {class_name}.{attr_name} '
            f'is a mutable class attribute; initialize in __init__/__new__'
        )

    def visit_ClassDef(self, node: ast.ClassDef):
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                if not _is_mutable_value(stmt.value):
                    continue
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and _should_flag_name(target.id):
                        self._report(stmt, node.name, target.id)
            elif isinstance(stmt, ast.AnnAssign):
                if not _is_mutable_value(stmt.value):
                    continue
                target = stmt.target
                if isinstance(target, ast.Name) and _should_flag_name(target.id):
                    self._report(stmt, node.name, target.id)
        self.generic_visit(node)


def main() -> int:
    errors: list[str] = []
    for path in sorted(ROOT.rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        visitor = Visitor(path)
        visitor.visit(tree)
        errors.extend(visitor.errors)

    if errors:
        print('Mutable class attribute check failed:')
        for err in errors:
            print(f'  {err}')
        return 1
    print('Mutable class attribute check passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
