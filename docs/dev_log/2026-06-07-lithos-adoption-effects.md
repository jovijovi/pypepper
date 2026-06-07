---
title: "Finish PyPepper Lithos adoption/effects evaluation surface"
status: archived
created_at: 2026-06-07
archived_at: 2026-06-07
---
# Finish PyPepper Lithos adoption/effects evaluation surface

## Task Background

A previous broad run on the `test/lithos-adoption-effects` branch was
interrupted, leaving only `docs/lithos/evaluation-plan.md`,
`scripts/build_docs_index.py`, and `scripts/docs_drift_signal.py`. The task was
to finish a concise but complete Lithos full-lifecycle governance adoption /
effects evaluation surface for PyPepper, using current single-model Lithos
language, without changing product runtime code, committing, pushing, opening
PRs, or running long tests.

Scope was governance/docs/tooling only. Product runtime under `pypepper/` and
product tests under `tests/` were out of scope. The branch is an evaluation
branch, not a release.

## Problems Encountered

### P1 — Existing evaluation-plan.md had no frontmatter

`scripts/build_docs_index.py` requires every `docs/**/*.md` to carry a YAML
frontmatter block (`title`, `status`, `created_at`). The pre-existing
`docs/lithos/evaluation-plan.md` started directly with a Markdown heading, so a
full index build would have errored on it.

### P2 — A whole-repo static safety scan would flag legacy product artifacts

PyPepper ships cryptographic helpers and tests (`common.security.crypto`) whose
fixtures can match secret/key shapes, and product code may carry legacy task
markers. A naive repo-wide scan would report findings unrelated to the adoption
diff, making the gate look red for the wrong reasons.

### P3 — Scanners must not match their own committed source

A static safety scan and a governance verifier are themselves committed text the
scan reads. Pattern literals (secret shapes, private-path literals, placeholder
markers) stored verbatim would make the scanner flag itself.

## Root Cause Analysis

### RC1 — Index contract is strict by design

The index builder treats missing frontmatter as an error so the catalogue stays
complete and machine-checkable. The fix is to make the document conform, not to
relax the builder.

### RC2 — The overlay governs only what it adds

The evaluation branch governs the artifacts it introduces; it does not own the
legacy product tree. Conflating the two scopes is the root of the false
positives, so the scan scope — not its rules — must be narrowed.

### RC3 — Self-reference is inherent to text scanners

Any scanner over committed text can see its own needles. Lithos resolves this
with two rules: assemble needles from fragments (no self-match) and self-test on
dynamically built probes.

## Solution

- Added the authority chain: `GOAL.md`, `docs/AI_FLOW.md`, and a single-model
  manifest `docs/lithos-adoption-manifest.json`
  (`governance_model: full-lifecycle-governance`).
- Added the effects summary `docs/lithos/adoption-evaluation.md` mapping the six
  effects from the plan, with the Hermes-reported pre-adoption baseline.
- Added the knowledge spine: this dev_log, a lesson, a practice, root
  `LESSONS.md`, and `docs/practices/README.md`.
- Added frontmatter to `docs/lithos/evaluation-plan.md` (fixes P1).
- Added `scripts/static_safety_scan.py` — a conservative, stdlib-only scanner
  scoped to the adoption surface by default with an opt-in `--all` whole-repo
  sweep (fixes P2); every needle and self-test probe is fragment-assembled
  (fixes P3).
- Added `scripts/verify_lithos_adoption.py` — one command that checks required
  governance files, required semantic markers, single-model language, docs index
  freshness, drift report freshness, manifest JSON shape, the static safety
  scan, and `py_compile` for the added scripts.
- Minimal additive edits to `AGENTS.md` (Lithos adoption section with the
  Hermes/Claude/Codex role split) and `.github/pull_request_template.md`
  (Lithos/evaluation evidence fields).
- Generated `docs/INDEX.md` and `docs/lessons/_drift_report.md`.

## Alternatives Considered

- **Whole-repo static scan by default** — rejected: it conflates adoption-surface
  safety with legacy-repo cleanliness and produces owner-unrelated noise. Kept as
  an honest opt-in (`--all`).
- **A separate verifier per gate** — rejected for friction; a single aggregating
  verifier suits a small toolkit while still invoking the focused scripts.
- **Re-running the product suite to claim post-adoption pass** — rejected:
  out of scope (no long tests), and behavior evidence is the owner/controller's
  to run. Only the controller-reported baseline is recorded.

## Verification

All commands below were run from the repository root. Claude Code authored the main adoption docs but repeatedly timed out before producing a final result; Hermes completed narrow verifier glue and ran the gates as controller/verifier.

```
$ python -m py_compile scripts/build_docs_index.py scripts/docs_drift_signal.py scripts/static_safety_scan.py scripts/verify_lithos_adoption.py
# passed

$ python scripts/docs_drift_signal.py --self-test
docs_drift_signal self-test passed.

$ python scripts/build_docs_index.py --write
wrote docs/INDEX.md (7 docs)

$ python scripts/docs_drift_signal.py --write
wrote docs/lessons/_drift_report.md

$ python scripts/static_safety_scan.py --self-test
static safety self-test passed

$ python scripts/static_safety_scan.py
Static safety scan passed. Scope: Lithos adoption surface; files scanned: 19.

$ python scripts/verify_lithos_adoption.py
PyPepper Lithos adoption verification passed.
Checked 18 required files and 4 scripts.

$ uv run make test
106 passed in 27.88s; total coverage 88%.

$ git diff --check
# passed
```

Exploratory broader scan (`python scripts/static_safety_scan.py --all`) is intentionally reported separately: it flags pre-existing product/config/test surfaces outside this adoption branch's default scope, including legacy private-path-shaped config and crypto/key-shaped product fixtures. That does not invalidate the adoption-surface gate.

## Follow-up Notes

- Codex CLI independent review initially failed in `read-only` sandbox because of the known `bwrap` loopback error, then succeeded in review-only `danger-full-access -a never` mode with pre/post checksum comparison clean.
- Final Codex verdict: `VERDICT: PASS`; `BLOCKERS: None`.
- The lesson and practice created here are new (born active); no prior knowledge
  doc was cited, so no use-driven re-validation was due this task.
- Left ready, not enabled: CI wiring of `scripts/verify_lithos_adoption.py`.
- Cross-references:
  [lesson](../lessons/2026-06-07-lithos-adoption-effects.md),
  [practice](../practices/2026-06-07-lithos-evaluation-branch.md).
