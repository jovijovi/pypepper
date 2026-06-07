#!/usr/bin/env python3
"""Verify PyPepper's Lithos adoption/effects evaluation surface."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "GOAL.md",
    "LESSONS.md",
    "AGENTS.md",
    ".github/pull_request_template.md",
    "docs/AI_FLOW.md",
    "docs/INDEX.md",
    "docs/lithos/evaluation-plan.md",
    "docs/lithos/adoption-evaluation.md",
    "docs/lithos-adoption-manifest.json",
    "docs/dev_log/2026-06-07-lithos-adoption-effects.md",
    "docs/lessons/2026-06-07-lithos-adoption-effects.md",
    "docs/lessons/_drift_report.md",
    "docs/practices/README.md",
    "docs/practices/2026-06-07-lithos-evaluation-branch.md",
    "scripts/build_docs_index.py",
    "scripts/docs_drift_signal.py",
    "scripts/static_safety_scan.py",
    "scripts/verify_lithos_adoption.py",
]

REQUIRED_MARKERS = {
    "GOAL.md": [
        "full-lifecycle governance",
        "No runtime behavior changes",
        "Document authority chain",
    ],
    "docs/AI_FLOW.md": [
        "AGENT role split",
        "Hermes",
        "Claude Code",
        "Codex CLI",
        "static safety scan is safety evidence only",
    ],
    "docs/lithos/adoption-evaluation.md": [
        "six effects",
        "106 tests",
        "static safety scan is **safety evidence only",
        "one full-lifecycle model",
    ],
    "AGENTS.md": [
        "Lithos adoption evaluation",
        "Hermes",
        "Claude Code",
        "Codex CLI",
    ],
    ".github/pull_request_template.md": [
        "Lithos / Governance Evidence",
        "full-lifecycle governance",
    ],
}

STALE_ACTIVE_CONFORMANCE_PHRASES = [
    "adoption_profile",
    "\"depth\"",
    "lighter-governed-workflow",
    "full-governed-project",
    "minimal conformance",
    "lite conformance",
]

ADDED_SCRIPTS = [
    "scripts/build_docs_index.py",
    "scripts/docs_drift_signal.py",
    "scripts/static_safety_scan.py",
    "scripts/verify_lithos_adoption.py",
]


def _run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _read(rel: str) -> str:
    return (PROJECT_ROOT / rel).read_text(encoding="utf-8")


def check_required_files(errors: list[str]) -> None:
    for rel in REQUIRED_FILES:
        path = PROJECT_ROOT / rel
        if not path.is_file():
            errors.append(f"missing required file: {rel}")


def check_markers(errors: list[str]) -> None:
    for rel, markers in REQUIRED_MARKERS.items():
        path = PROJECT_ROOT / rel
        if not path.is_file():
            continue
        text = _read(rel)
        for marker in markers:
            if marker not in text:
                errors.append(f"{rel}: missing marker {marker!r}")


def check_single_model_language(errors: list[str]) -> None:
    manifest = PROJECT_ROOT / "docs/lithos-adoption-manifest.json"
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data.get("governance_model") != "full-lifecycle-governance":
            errors.append("docs/lithos-adoption-manifest.json: governance_model must be full-lifecycle-governance")
        if "adoption_profile" in data:
            errors.append("docs/lithos-adoption-manifest.json: adoption_profile is not allowed")
        if "depth" in data:
            errors.append("docs/lithos-adoption-manifest.json: depth is not allowed")
        claim = data.get("conformance_claim", {})
        if not isinstance(claim, dict) or claim.get("claims_conformance") is not True:
            errors.append("docs/lithos-adoption-manifest.json: conformance_claim.claims_conformance must be true")
        if not str(claim.get("statement", "")).strip():
            errors.append("docs/lithos-adoption-manifest.json: conformance claim statement is required")
    for rel in [
        "GOAL.md",
        "docs/AI_FLOW.md",
        "docs/lithos/evaluation-plan.md",
        "docs/lithos/adoption-evaluation.md",
        "docs/lithos-adoption-manifest.json",
        "docs/dev_log/2026-06-07-lithos-adoption-effects.md",
        "docs/lessons/2026-06-07-lithos-adoption-effects.md",
        "docs/practices/2026-06-07-lithos-evaluation-branch.md",
        "AGENTS.md",
    ]:
        path = PROJECT_ROOT / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in STALE_ACTIVE_CONFORMANCE_PHRASES:
            if phrase in text:
                errors.append(f"{rel}: stale active conformance phrase {phrase!r}")


def check_subcommand(errors: list[str], cmd: list[str]) -> None:
    code, stdout, stderr = _run(cmd)
    if code != 0:
        joined = (stderr or stdout).strip().splitlines()
        detail = joined[0] if joined else "no output"
        errors.append(f"subcheck failed: {' '.join(cmd)}: {detail}")


def main() -> int:
    errors: list[str] = []
    check_required_files(errors)
    check_markers(errors)
    check_single_model_language(errors)

    if not errors:
        check_subcommand(errors, [sys.executable, "scripts/build_docs_index.py", "--check"])
        check_subcommand(errors, [sys.executable, "scripts/docs_drift_signal.py", "--self-test"])
        check_subcommand(errors, [sys.executable, "scripts/docs_drift_signal.py", "--check"])
        check_subcommand(errors, [sys.executable, "scripts/static_safety_scan.py", "--self-test"])
        check_subcommand(errors, [sys.executable, "scripts/static_safety_scan.py"])
        check_subcommand(errors, [sys.executable, "-m", "py_compile", *ADDED_SCRIPTS])

    if errors:
        print("Lithos adoption verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("PyPepper Lithos adoption verification passed.")
    print(f"Checked {len(REQUIRED_FILES)} required files and {len(ADDED_SCRIPTS)} scripts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
