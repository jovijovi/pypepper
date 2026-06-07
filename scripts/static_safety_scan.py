#!/usr/bin/env python3
"""Static safety scan for the PyPepper Lithos adoption surface.

Default scope is the governance/adoption surface added by this evaluation branch,
not the entire historical product repository. Use ``--all`` for an exploratory
whole-repo sweep; report that broader result separately.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ADOPTION_PATHS = (
    "AGENTS.md",
    ".github/pull_request_template.md",
    "GOAL.md",
    "LESSONS.md",
    "docs",
    "scripts/build_docs_index.py",
    "scripts/docs_drift_signal.py",
    "scripts/static_safety_scan.py",
    "scripts/verify_lithos_adoption.py",
)

TEXT_EXTENSIONS = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

SKIP_DIRS = {
    ".git",
    ".codegraph",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
}

# Build sensitive needles from fragments so the scanner does not match its own
# source. Labels stay generic/vendor-neutral.
PRIVATE_PATH_PATTERNS = [
    re.compile(part_a + part_b) for part_a, part_b in (
        (r"/ho", r"me/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._~+/-]+)?"),
        (r"/Use", r"rs/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._~+/-]+)?"),
        (r"/ro", r"ot(?:/[A-Za-z0-9._~+/-]+)?"),
        (r"[A-Za-z]:\\\\Use", r"rs\\\\[A-Za-z0-9._-]+(?:\\\\[A-Za-z0-9._~+/-]+)?"),
    )
]

SECRET_PATTERNS = [
    re.compile(part_a + part_b, re.IGNORECASE) for part_a, part_b in (
        (r"-----BEGIN ", r"(?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
        (r"\b(?:api[_-]?key|token|secret|password|private[_-]?key)\b\s*[:=]\s*", r"['\"]?[A-Za-z0-9_./+=-]{16,}['\"]?"),
        (r"\b[A-Za-z0-9_]{8,}_", r"(?:TOKEN|SECRET|PASSWORD|KEY)\s*=\s*['\"]?[A-Za-z0-9_./+=-]{16,}['\"]?"),
    )
]

PLACEHOLDER_PATTERNS = [
    re.compile(part_a + part_b, re.IGNORECASE) for part_a, part_b in (
        (r"\bREPLACE_", r"WITH_[A-Z0-9_]+\b"),
        (r"\bTO", r"DO\b"),
        (r"\bT", r"BD\b"),
        (r"\bFIX", r"ME\b"),
    )
]


def _is_text_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS


def _walk_path(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if _is_text_file(root) else []
    if not root.is_dir():
        return []
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.relative_to(PROJECT_ROOT).parts):
            continue
        if _is_text_file(path):
            files.append(path)
    return files


def _default_files() -> list[Path]:
    files: list[Path] = []
    for rel in ADOPTION_PATHS:
        files.extend(_walk_path(PROJECT_ROOT / rel))
    return sorted(set(files))


def _all_files() -> list[Path]:
    return _walk_path(PROJECT_ROOT)


def scan_files(files: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in files:
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, patterns in (
            ("private machine-local path", PRIVATE_PATH_PATTERNS),
            ("secret-shaped value", SECRET_PATTERNS),
            ("unfinished-work placeholder", PLACEHOLDER_PATTERNS),
        ):
            for pattern in patterns:
                if pattern.search(text):
                    findings.append(f"{rel}: {label}")
                    break
    return findings


def _self_test() -> int:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        probes = {
            "clean.md": "# clean\nNo sensitive material here.\n",
            "private-path.md": "machine path: " + "/ho" + "me/example/workspace\n",
            "secret-value.md": "token = " + "a" * 20 + "\n",
            "placeholder.md": "value: " + "REPLACE_" + "WITH_OUTPUT" + "\n",
        }
        expected = {
            "private-path.md": "private machine-local path",
            "secret-value.md": "secret-shaped value",
            "placeholder.md": "unfinished-work placeholder",
        }
        paths = []
        for name, content in probes.items():
            p = root / name
            p.write_text(content, encoding="utf-8")
            paths.append(p)
        # Inline mini scan so PROJECT_ROOT-relative reporting is not involved.
        got: dict[str, str] = {}
        for p in paths:
            text = p.read_text(encoding="utf-8")
            for label, patterns in (
                ("private machine-local path", PRIVATE_PATH_PATTERNS),
                ("secret-shaped value", SECRET_PATTERNS),
                ("unfinished-work placeholder", PLACEHOLDER_PATTERNS),
            ):
                if any(pattern.search(text) for pattern in patterns):
                    got[p.name] = label
                    break
        if got != expected:
            print(f"self-test failed: expected={expected!r} got={got!r}", file=sys.stderr)
            return 2
    print("static safety self-test passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="scan all repository text files instead of only the adoption surface")
    parser.add_argument("--self-test", action="store_true", help="run scanner self-test and exit")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    files = _all_files() if args.all else _default_files()
    findings = scan_files(files)
    if findings:
        print("Static safety scan failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1
    scope = "whole repository" if args.all else "Lithos adoption surface"
    print(f"Static safety scan passed. Scope: {scope}; files scanned: {len(files)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
