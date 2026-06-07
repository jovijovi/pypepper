#!/usr/bin/env python3
"""Activity-aware drift signal for lessons and practices.

Part of PyPepper's Lithos adoption (single full-lifecycle governance model).
For each lesson or practice that declares ``applies_to`` paths in frontmatter,
check whether any of those paths changed in git history after the doc's
``last_validated_at`` boundary. Output a summary to
``docs/lessons/_drift_report.md`` so future contributors know which knowledge
artifacts may need re-validation.

Boundaries are evaluated against absolute commit timestamps (git ``%ct``), and a
date-only ``last_validated_at`` is anchored to the end of that day in UTC, so the
report is identical regardless of the runner's timezone. Run ``--self-test`` to
verify this boundary logic without touching a repository.

Usage::

    python scripts/docs_drift_signal.py --write       # regenerate the report
    python scripts/docs_drift_signal.py --check        # fail if the report is stale
    python scripts/docs_drift_signal.py --self-test    # verify boundary logic only
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = PROJECT_ROOT / "docs"
REPORT_PATH = DOCS_ROOT / "lessons" / "_drift_report.md"


def _parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    block = text[4:end].splitlines()
    data: dict = {}
    current_list_key: str | None = None
    for line in block:
        if not line.strip():
            current_list_key = None
            continue
        if line.startswith("  - ") and current_list_key is not None:
            data[current_list_key].append(line[4:].strip().strip('"').strip("'"))
            continue
        match = re.match(r"^([\w_]+):\s*(.*)$", line)
        if not match:
            current_list_key = None
            continue
        key, value = match.group(1), match.group(2).strip()
        if not value:
            data[key] = []
            current_list_key = key
            continue
        data[key] = value.strip('"').strip("'")
        current_list_key = None
    return data


def _is_git_working_tree() -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return result.stdout.strip() == "true"


def _project_prefix() -> str:
    """Return the path from the repository root down to ``PROJECT_ROOT``.

    ``git diff-tree`` reports paths relative to the repository root, while the
    knowledge docs and their validation paths are expressed relative to
    ``PROJECT_ROOT``. ``git rev-parse --show-prefix`` (evaluated at
    ``PROJECT_ROOT``) yields the connecting prefix, or an empty string when
    ``PROJECT_ROOT`` is itself the repository root.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-prefix"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return result.stdout.strip()


def _repo_relative(path: str, prefix: str) -> str:
    """Translate a ``PROJECT_ROOT``-relative path into its repo-root form.

    Pure string logic so ``--self-test`` can exercise it without a repository.
    """
    norm = prefix.strip().strip("/")
    if not norm:
        return path
    return f"{norm}/{path}"


def _commit_touches_path(commit: str, path: str) -> bool:
    target = _repo_relative(path, _project_prefix())
    try:
        result = subprocess.run(
            ["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit, "--", path],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return any(line.strip() == target for line in result.stdout.splitlines())


def _validation_threshold_epoch(last_validated: str) -> float | None:
    """Return the epoch boundary that separates validated from drifting commits.

    A commit is drift only when its absolute timestamp is strictly greater than
    this boundary. A date-only ``YYYY-MM-DD`` is anchored to ``23:59:59.999999``
    UTC of that date; an ISO 8601 datetime is honored exactly (a trailing ``Z``
    or a naive value is treated as UTC). Empty or unparseable values return
    ``None`` (no boundary, no drift).
    """
    raw = last_validated.strip()
    if not raw:
        return None
    try:
        day = date.fromisoformat(raw)
    except ValueError:
        day = None
    if day is not None:
        return datetime.combine(day, time.max, tzinfo=timezone.utc).timestamp()
    iso = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        moment = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


def _git_log_changes(path: str, last_validated: str, validation_doc: str) -> list[str]:
    """Return commits touching ``path`` after the ``last_validated`` boundary.

    Commits are filtered by their absolute committer timestamp (git ``%ct``).
    Commits that also update ``validation_doc`` are treated as re-validation
    changes and excluded.
    """
    threshold = _validation_threshold_epoch(last_validated)
    if threshold is None:
        return []
    try:
        result = subprocess.run(
            ["git", "log", "--format=%H%x00%ct%x00%h %s", "--no-merges", "--", path],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    changes: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split("\0")
        if len(parts) != 3:
            continue
        commit, raw_epoch, summary = parts
        try:
            commit_epoch = int(raw_epoch)
        except ValueError:
            continue
        if commit_epoch <= threshold:
            continue
        if _commit_touches_path(commit, validation_doc):
            continue
        changes.append(summary)
    return changes


def _scan_knowledge_docs() -> list[tuple[str, dict]]:
    found: list[tuple[str, dict]] = []
    for subdir in ("lessons", "practices"):
        base = DOCS_ROOT / subdir
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            if path.name.startswith("_") or path.name == "README.md":
                continue
            fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
            if fm is not None:
                found.append((path.relative_to(DOCS_ROOT).as_posix(), fm))
    return found


def _build_report() -> str:
    docs = _scan_knowledge_docs()
    drifts: list[dict] = []
    skipped_no_applies = 0
    skipped_no_validation_date = 0
    for rel, fm in docs:
        applies_to = fm.get("applies_to") or []
        if not applies_to:
            skipped_no_applies += 1
            continue
        last_validated = str(fm.get("last_validated_at") or "").strip()
        if not last_validated:
            skipped_no_validation_date += 1
            continue
        per_path: dict[str, list[str]] = {}
        validation_doc = f"docs/{rel}"
        for code_path in applies_to:
            commits = _git_log_changes(code_path, last_validated, validation_doc)
            if commits:
                per_path[code_path] = commits[:5]
        if per_path:
            drifts.append({
                "doc": rel,
                "title": str(fm.get("title", rel)).strip(),
                "last_validated_at": last_validated,
                "drifts": per_path,
            })
    out: list[str] = [
        "<!-- AUTO-GENERATED by scripts/docs_drift_signal.py — do not hand-edit -->",
        "",
        "# Lesson / practice drift report",
        "",
        f"Knowledge docs scanned: {len(docs)}",
        f"With drift candidates: **{len(drifts)}**",
        f"Skipped (no `applies_to`): {skipped_no_applies}",
        f"Skipped (no `last_validated_at`): {skipped_no_validation_date}",
        "",
    ]
    if not drifts:
        out.append(
            "No drift candidates. All knowledge docs are in sync with their "
            "`applies_to` paths after their `last_validated_at` boundary."
        )
        out.append("")
    else:
        out.append("## Candidates")
        out.append("")
        out.append(
            "Commits that also update the validating knowledge doc are treated "
            "as re-validation changes and excluded from this report."
        )
        out.append("")
        for item in drifts:
            doc_rel = item["doc"]
            href = doc_rel[len("lessons/"):] if doc_rel.startswith("lessons/") else "../" + doc_rel
            out.append(f"### [{item['title']}]({href})")
            out.append("")
            out.append(f"- Doc: `{item['doc']}`")
            out.append(f"- Last validated: {item['last_validated_at']}")
            out.append("- Recent commits touching `applies_to` paths:")
            for code_path, commits in item["drifts"].items():
                out.append(f"  - `{code_path}`:")
                for commit in commits:
                    out.append(f"    - {commit}")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def _run_self_test() -> int:
    """Verify the drift boundary logic without touching a repository."""
    failures: list[str] = []

    def expect(label: str, condition: bool) -> None:
        if not condition:
            failures.append(label)

    utc = timezone.utc

    day_boundary = _validation_threshold_epoch("2026-06-05")
    expect("date-only value parses to a boundary", day_boundary is not None)
    if day_boundary is not None:
        expect(
            "midnight start of the validated day is in-sync",
            datetime(2026, 6, 5, 0, 0, 0, tzinfo=utc).timestamp() <= day_boundary,
        )
        expect(
            "late commit on the validated day is in-sync",
            datetime(2026, 6, 5, 22, 20, 16, tzinfo=utc).timestamp() <= day_boundary,
        )
        expect(
            "evening commit in a +08:00 zone is in-sync",
            datetime(2026, 6, 5, 23, 0, 0, tzinfo=timezone(timedelta(hours=8))).timestamp() <= day_boundary,
        )
        expect(
            "start of the next day is drift",
            datetime(2026, 6, 6, 0, 0, 0, tzinfo=utc).timestamp() > day_boundary,
        )

    exact_boundary = _validation_threshold_epoch("2026-06-05T12:00:00+00:00")
    expect("ISO datetime value parses to a boundary", exact_boundary is not None)
    if exact_boundary is not None:
        expect(
            "commit one second before the timestamp is in-sync",
            datetime(2026, 6, 5, 11, 59, 59, tzinfo=utc).timestamp() <= exact_boundary,
        )
        expect(
            "commit exactly at the timestamp is in-sync",
            datetime(2026, 6, 5, 12, 0, 0, tzinfo=utc).timestamp() <= exact_boundary,
        )
        expect(
            "commit one second after the timestamp is drift",
            datetime(2026, 6, 5, 12, 0, 1, tzinfo=utc).timestamp() > exact_boundary,
        )

    expect(
        "a trailing Z is treated as UTC",
        _validation_threshold_epoch("2026-06-05T12:00:00Z") == exact_boundary,
    )
    expect(
        "a naive datetime is treated as UTC",
        _validation_threshold_epoch("2026-06-05T12:00:00") == exact_boundary,
    )
    expect("an empty value has no boundary", _validation_threshold_epoch("") is None)
    expect("an unparseable value has no boundary", _validation_threshold_epoch("not a date") is None)

    expect(
        "a nested-project prefix is prepended to the path",
        _repo_relative("docs/practices/x.md", "examples/governed-project/")
        == "examples/governed-project/docs/practices/x.md",
    )
    expect(
        "a prefix missing its trailing slash still joins cleanly",
        _repo_relative("docs/x.md", "templates/governed-project")
        == "templates/governed-project/docs/x.md",
    )
    expect(
        "an empty prefix (project at repo root) leaves the path unchanged",
        _repo_relative("docs/x.md", "") == "docs/x.md",
    )
    expect(
        "a bare-slash prefix leaves the path unchanged",
        _repo_relative("docs/x.md", "/") == "docs/x.md",
    )

    if failures:
        print("docs_drift_signal self-test failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("docs_drift_signal self-test passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--self-test", action="store_true", help="verify boundary logic without a repository")
    args = parser.parse_args()
    if args.self_test:
        return _run_self_test()
    if not args.write and not args.check:
        args.write = True
    if not _is_git_working_tree():
        print("ERROR: docs_drift_signal.py must run inside a git working tree.", file=sys.stderr)
        return 2
    rendered = _build_report()
    if args.check:
        existing = REPORT_PATH.read_text(encoding="utf-8") if REPORT_PATH.exists() else ""
        if existing != rendered:
            print(
                "ERROR: docs/lessons/_drift_report.md is stale. "
                "Run `python scripts/docs_drift_signal.py --write` and commit.",
                file=sys.stderr,
            )
            return 1
        print("OK: drift report up to date")
        return 0
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(rendered, encoding="utf-8")
    print(f"wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
