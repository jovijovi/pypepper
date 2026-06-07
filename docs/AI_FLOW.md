---
title: "Local AI-collaboration workflow"
status: active
created_at: 2026-06-07
last_validated_at: 2026-06-07
---
# Local AI-collaboration workflow (AI_FLOW)

The single source of truth for how AI agents collaborate on PyPepper under
Lithos full-lifecycle governance. Read this before making any change. It sits
under [GOAL.md](../GOAL.md) in the document authority chain.

## AGENT role split

Lithos assigns every responsibility a named holder; approval authority is never
held by an implementation agent.

| Lithos role | Holder on this branch | Responsibility |
| --- | --- | --- |
| owner | PyPepper maintainer (human) | Holds all approvals; accountable for the branch. Approval is non-delegable. |
| controller | Hermes | Drives the session, manages worktree/branch and GitHub operations, enforces gates, arbitrates evidence, reports. |
| architect | Hermes (plan + acceptance criteria), owner sign-off | Owns the evaluation plan, scope, and acceptance gates. |
| implementation_agent | Claude Code (Opus) | Produces the governance/docs/tooling change. Proposes; never self-approves. |
| reviewer | Codex CLI | Independent critical review of the branch, blockers, and claimed effects. |
| verifier | Codex CLI and Hermes | Confirm with reproducible evidence, independent of implementation. |

Review and verification are kept independent of implementation. Where roles are
combined (controller also acts as a verifier of arbitration), this file states
it so the combination is a choice, not an accident.

## Approvals and approval gates

Four layered gates; clearing one never clears a higher one.

1. **Preparation** — standing authorization. Reading code, planning, and
   drafting governance docs need no per-action owner approval.
2. **Implementation** — owner approval required before changes land. The
   implementation agent proposes the diff; the owner (via Hermes) approves.
3. **Destructive / external** — owner approval required per action: commits,
   pushes, merges, branch deletion, external delivery.
4. **Live / runtime** — out of scope on this branch; even so, owner approval
   and separate controls remain mandatory and were not granted.

## Worktree and branch discipline

- All work happens in the isolated worktree on branch
  `test/lithos-adoption-effects`, never on `main`.
- Product runtime code under `pypepper/` and product tests under `tests/` are
  not modified on this branch.
- Branch operations (create, push, delete) are controller actions under owner
  approval, not implementation-agent actions.

## Verification gates

Run from the repository root. These are governance checks, not a substitute for
product tests.

- Product tests (owner/controller-run baseline): `uv run make test`
  — or `make test` directly (`pytest --cov=pypepper tests/`).
- Docs index freshness: `python scripts/build_docs_index.py --check`
- Drift report freshness: `python scripts/docs_drift_signal.py --check`
- Static safety scan (adoption surface): `python scripts/static_safety_scan.py`
- Governance verifier (aggregates the above): `python scripts/verify_lithos_adoption.py`
- Scripts compile: `python -m py_compile scripts/*.py`
- `git diff --check` passes (no whitespace/conflict artifacts).

Reproducible behavior evidence (tests/CI) is required for any behavioral
change. The static safety scan is safety evidence only; it is not behavior
evidence and clears no approval gate.

## Non-approvals

The implementation agent must not, without explicit owner approval: change
`pypepper/` runtime behavior; edit product tests; commit, push, merge, delete
branches, or release/publish; open or auto-merge pull requests; enable any
live/runtime default; or add secrets, tokens, or private machine paths to
committed text. A pull request, if opened, stays Draft until the owner approves
ready-for-review.
