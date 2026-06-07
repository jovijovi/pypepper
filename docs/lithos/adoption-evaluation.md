---
title: "Lithos adoption evaluation — six effects"
status: active
created_at: 2026-06-07
last_validated_at: 2026-06-07
---
# Lithos adoption evaluation — six effects

Summary of the effects defined in [evaluation-plan.md](evaluation-plan.md),
assessed for this branch. PyPepper adopts exactly one governance model: Lithos
**full-lifecycle governance**. There are no adoption tiers or profiles; a small
toolkit keeps the anchors concise but never omits them.

## Baseline and post-adoption behavior evidence

Hermes (controller) ran `uv run make test` with docker compose services up
(`docker compose -f devenv/ci.yaml up -d`) before and after the governance
overlay. Both runs passed **106 tests**; the post-adoption run completed in
27.88 seconds with total coverage reported at 88%. No product runtime files
under `pypepper/` or product tests under `tests/` were changed on this branch.

## The six effects

### 1. Authority and scope effect

`GOAL.md` and `docs/AI_FLOW.md` give a clear goal, role split, approval gates,
and non-approvals, so an agent knows where to look before changing anything.
**Improved** — authority is now explicit and repo-local.

### 2. Verification effect

The existing test command stays real and runnable
(`uv run make test` / `make test`). A governance verifier
(`scripts/verify_lithos_adoption.py`) checks governance artifacts without
replacing product tests. **Improved**, scoped to governance.

### 3. Knowledge-retention effect

Dev logs, lessons, practices, a generated `docs/INDEX.md`, and a drift report
preserve reusable learning without bloating `README.md` or chat history.
**Improved**; long-term value depends on continued use-driven validation.

### 4. Safety and release-boundary effect

`scripts/static_safety_scan.py` and the PR checklist make secret-shaped values,
private machine paths, and unfinished-work placeholders visible, and surface
release assumptions. The static safety scan is **safety evidence only; it is
not behavior evidence** and clears no approval gate. **Improved** for safety
visibility.

### 5. Agent-collaboration effect

`AGENTS.md` routes Claude Code (implementation) and Codex CLI (review) roles,
and the branch preserves the Hermes / Claude Code / Codex responsibility
separation. **Improved** — the split is written down, not implicit.

### 6. Friction effect

The added structure is concise and reuses PyPepper's existing `scripts/` and
`docs/` conventions. No minimal/lite/lighter-vs-full conformance tiers are
reintroduced; one full-lifecycle model is kept lightweight. **Acceptable** for
a small toolkit; the main ongoing cost is regenerating the index and drift
report when knowledge docs change.

## Uncertain / out of scope

- Whether the knowledge spine stays maintained over time (depends on
  use-driven validation actually being performed).
- CI wiring of the governance gates (left ready; not enabled here).
