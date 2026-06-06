#!/usr/bin/env python3
"""Static safety scan for the PyPepper Lithos adoption surface.

A first-class, machine-runnable governance gate adapted from the Lithos standard
(see ``docs/AI_FLOW.md`` and https://github.com/jovijovi/lithos). This pure
standard-library scanner reads committed text and rejects three classes of value
that must never enter a governed repository:

* secret-shaped tokens (credential, key, and private-key material);
* private, machine-local absolute filesystem paths that leak a contributor's
  environment into shared text;
* unfinished-work markers that signal text was offered as done before it was.

A green run is reproducible evidence a third party can regenerate, not testimony.
It is **safety evidence only** -- it never proves behavior, and passing it clears
no approval gate.

Scope on this evaluation branch
-------------------------------
By default the scan covers the **Lithos adoption surface** -- the governance
documents, manifest, and scripts this branch introduces or owns -- listed in
``GOVERNED_SURFACE`` below. The pre-existing ``pypepper/`` runtime tree is
deliberately out of the default scope: it carries long-standing task-marker
comments, and rewriting runtime source is out of scope for a behavior-neutral
evaluation branch. That is a declared conformance gap, recorded in
``docs/lithos/evaluation-report.md``; it is honestly demonstrable with ``--all``,
which scans every text file in the repository and will report those legacy
markers. Narrowing the *paths* scanned never drops a *finding class*: all three
classes above are always enforced wherever the scan looks.

Usage
-----
    python3 scripts/verify_static_safety.py            # scan the adoption surface
    python3 scripts/verify_static_safety.py --all      # scan the whole repository
    python3 scripts/verify_static_safety.py PATH ...   # scan specific files/dirs

Two design rules keep the scanner honest:

1. **No self-match.** Every sensitive needle is assembled from split fragments,
   so this file never contains a value one of its own patterns would flag.
2. **Self-test.** Before scanning, the engine runs on dynamically constructed
   probes -- secret-like strings built at runtime, never stored as literals --
   and confirms it flags the bad ones and clears a clean one, so a clean scan
   means the engine works rather than that it silently matched nothing.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The Lithos adoption surface this branch governs. Repo-relative; a directory is
# scanned recursively. Keep this list in sync with the artifacts the adoption
# introduces or owns.
GOVERNED_SURFACE = [
    "docs/AI_FLOW.md",
    "docs/lithos",
    "AGENTS.md",
    "README.md",
    ".github/pull_request_template.md",
    "scripts/verify_static_safety.py",
    "scripts/verify_lithos_conformance.py",
]

# Directories that are never committed governed text: version-control internals,
# caches, virtualenvs, and local service-data volumes (e.g. docker-compose mounts
# under devenv) that may be unreadable and are not part of the repository's text.
SKIP_PARTS = {
    ".git",
    ".codegraph",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "node_modules",
    ".data",
    "dist",
}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".svg"}
TEXT_SUFFIXES = {
    "",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".py",
    ".json",
    ".toml",
    ".cfg",
    ".ini",
    ".gitignore",
}

# Secret/token shapes. Each needle is assembled from fragments so this file
# never contains a value that matches one of its own patterns.
SECRET_PATTERNS = [
    re.compile("gh" + "p_[A-Za-z0-9]{20,}"),
    re.compile("github" + "_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?<![A-Za-z0-9])" + "sk-" + r"[A-Za-z0-9-]{20,}"),
    re.compile("AK" + "IA[A-Z0-9]{16}"),
    re.compile("xox" + r"[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile("-----BEGIN" + r"[A-Z ]*PRIVATE KEY-----"),
    re.compile(
        r"(?i)(api|access|secret|private|auth)[_-]?(key|token)\s*[:=]\s*"
        r"['\"]?[A-Za-z0-9_./+=-]{16,}"
    ),
]

# A private path token ends at a boundary: end-of-text, a path separator,
# whitespace, or common surrounding/terminating punctuation. Asserting this
# boundary -- rather than requiring the path to terminate the whole scanned
# text -- lets the patterns catch a private path embedded in prose, wrapped in
# quotes or backticks, or sitting just before a newline.
PRIVATE_PATH_BOUNDARY = r"""(?=$|[/\s`'")\]},:;.])"""

# The root account's home directory is a bare machine-local path with no
# username segment, so the literal itself is private. Assemble it from fragments
# so this file never stores the raw literal.
_ROOT_HOME = "/" + "root"

# Private, machine-local absolute paths. Covers Unix/macOS per-user home
# directories whether the path ends at the username leaf or continues deeper,
# the root account's home directory whether bare or with a subpath, and Windows
# per-user home directories on any drive letter with either separator style.
PRIVATE_PATH_PATTERNS = [
    re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+" + PRIVATE_PATH_BOUNDARY),
    re.compile(_ROOT_HOME + PRIVATE_PATH_BOUNDARY),
    re.compile(r"(?i)[A-Za-z]:[\\/]Users[\\/][^\\/\s]+"),
]

# Unfinished-work markers, assembled from fragments for the same reason. Matched
# case-sensitively except for the filler-text needle.
PLACEHOLDER_NEEDLES = [
    "TO" + "DO",
    "FIX" + "ME",
    "T" + "BD",
]
FILLER_NEEDLE = "lor" + "em"


def iter_text_files(targets: list[Path]) -> list[Path]:
    """Expand the requested targets into the concrete text files to scan."""
    files: set[Path] = set()
    for target in targets:
        if not target.exists():
            continue
        candidates = [target] if target.is_file() else target.rglob("*")
        for path in candidates:
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            if not path.is_file():
                continue
            if path.suffix.lower() in BINARY_SUFFIXES:
                continue
            if path.name == ".gitignore" or path.suffix.lower() in TEXT_SUFFIXES:
                files.add(path)
    return sorted(files)


def scan_text(label: str, text: str) -> list[str]:
    """Return a list of findings for a single document; empty means clean."""
    findings: list[str] = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(f"{label}: secret/token-shaped value")
            break
    for pattern in PRIVATE_PATH_PATTERNS:
        if pattern.search(text):
            findings.append(f"{label}: private machine-local absolute path")
            break
    for needle in PLACEHOLDER_NEEDLES:
        if needle in text:
            findings.append(f"{label}: unfinished-work marker ({needle})")
            break
    if FILLER_NEEDLE in text.lower():
        findings.append(f"{label}: filler placeholder text")
    return findings


def run_self_tests() -> list[str]:
    """Confirm the engine flags dynamically built bad probes and clears a clean one.

    Probes are constructed at runtime by concatenation so no credential-shaped
    literal is ever stored in this file.
    """
    failures: list[str] = []
    bad_probes = {
        "token-prefix-shape": "gh" + "p_" + "A" * 36,
        "long-access-token-shape": "github" + "_pat_" + "B" * 24,
        "secret-prefix-shape": "sk-" + "C" * 32,
        "hyphenated-secret-shape": "sk-" + "proj-" + "D" * 28,
        "cloud-access-key-shape": "AK" + "IA" + "E" * 16,
        "service-token-shape": "xox" + "b-" + "1" * 14,
        "private-key-header": "-----BEGIN" + " RSA PRIVATE KEY-----",
        "key-assignment": "api" + "_token" + "=" + "F" * 24,
        "home-path-nested": "/" + "home/" + "examplecontributor/" + "project",
        "home-path-leaf": "/" + "home/" + "examplecontributor",
        "users-path-leaf": "/" + "Users/" + "examplecontributor",
        "root-path-leaf": "/" + "root",
        "root-dotfile": "/" + "root/" + ".bash" + "rc",
        "windows-home": "C:" + chr(92) + "Users" + chr(92) + "alice" + chr(92) + "project",
        "home-path-quoted": "path=" + chr(34) + "/" + "home/" + "alice" + chr(34),
        "home-path-in-prose": "see " + "/" + "home/" + "examplecontributor" + " for details",
        "root-path-in-prose": "see " + "/" + "root" + " for details",
        "home-path-in-backticks": chr(96) + "/" + "home/" + "examplecontributor" + chr(96),
        "root-path-before-newline": "/" + "root" + chr(10) + "next line",
        "placeholder": "left a " + "TO" + "DO marker",
    }
    for label, probe in bad_probes.items():
        if not scan_text(label, probe):
            failures.append(f"self-test: scanner failed to flag {label!r}")
    clean_probes = {
        "prose": "A governed change ships with reproducible evidence and no secrets.",
        # 'task-' embeds the substring 'sk-' but is an ordinary hyphenated token,
        # not a secret; the secret pattern's left boundary must keep it clean.
        "hyphenated-task-token": "task-" + "1" * 30,
    }
    for label, probe in clean_probes.items():
        if scan_text(label, probe):
            failures.append(f"self-test: scanner flagged a known-clean probe ({label})")
    return failures


def resolve_targets(args: argparse.Namespace) -> tuple[list[Path], str]:
    """Resolve CLI arguments into the list of targets to scan and a scope label."""
    if args.paths:
        return [Path(p) if Path(p).is_absolute() else ROOT / p for p in args.paths], "requested paths"
    if args.all:
        return [ROOT], "the whole repository"
    return [ROOT / entry for entry in GOVERNED_SURFACE], "the Lithos adoption surface"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--all",
        action="store_true",
        help="scan every text file in the repository (reports legacy runtime markers)",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="specific files or directories to scan instead of the default surface",
    )
    args = parser.parse_args(argv)

    self_test_failures = run_self_tests()
    if self_test_failures:
        print("Static safety scan self-test failed:")
        for failure in self_test_failures:
            print(f"- {failure}")
        return 2

    targets, scope_label = resolve_targets(args)
    files = iter_text_files(targets)

    findings: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # treat as binary; nothing textual to scan
        except OSError:
            continue  # unreadable (permissions, transient): not committed text
        try:
            label = str(path.relative_to(ROOT))
        except ValueError:
            label = str(path)
        findings.extend(scan_text(label, text))

    if findings:
        print(f"Static safety scan failed (scope: {scope_label}):")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print(f"Static safety scan passed (scope: {scope_label}).")
    print(f"Self-tested the engine and scanned {len(files)} text files; no findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
