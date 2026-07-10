#!/usr/bin/env python3
"""Fail if pypepper classes declare mutable class-level instance state.

Detects patterns like:
  class Foo:
      _store = {}
      _lock = Lock()

Instance state must be initialized in __init__ / __new__.
Allowlisted intentional class constants are skipped.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'pypepper'

# Intentional shared class-level state (explicit singletons / class utilities)
ALLOWLIST_ATTRS = {
    ('network/http/sse/security.py', 'SSESecurityManager', '_rate_limit_cache'),
    ('network/http/sse/security.py', 'SSESecurityManager', '_rate_limit_lock'),
}

# Allowed for singleton __new__ guards (not per-instance state)
ALLOWLIST_ATTR_NAMES = {'_init_lock', '_instance'}


MUTABLE_CALLS = {'Lock', 'RLock', 'dict', 'list', 'set', 'Cache'}


class Visitor(ast.NodeVisitor):
    def __init__(self, path: Path):
        self.path = path
        self.errors: list[str] = []
        self._rel = str(path.relative_to(ROOT))

    def visit_ClassDef(self, node: ast.ClassDef):
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            if not isinstance(stmt.value, (ast.Dict, ast.List, ast.Set, ast.Call)):
                continue
            if isinstance(stmt.value, ast.Call):
                func = stmt.value.func
                name = None
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name not in MUTABLE_CALLS:
                    continue
            for target in stmt.targets:
                if isinstance(target, ast.Name) and (
                    target.id.startswith('_') or target.id == '__slots__'
                ):
                    if target.id == '__slots__':
                        continue
                    if target.id.isupper():
                        continue
                    if target.id in ALLOWLIST_ATTR_NAMES:
                        continue
                    key = (self._rel, node.name, target.id)
                    if key in ALLOWLIST_ATTRS:
                        continue
                    self.errors.append(
                        f'{self._rel}:{stmt.lineno}: class {node.name}.{target.id} '
                        f'is a mutable class attribute; initialize in __init__/__new__'
                    )
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
