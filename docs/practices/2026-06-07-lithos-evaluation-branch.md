---
title: "Adopt governance on a dedicated evaluation branch with concise full-lifecycle artifacts"
status: active
created_at: 2026-06-07
last_validated_at: 2026-06-07
description: "Trial a governance model on an existing product repo via an isolated branch that adds the complete full-lifecycle surface without touching runtime."
dev_log: docs/dev_log/2026-06-07-lithos-adoption-effects.md
tags: [lithos, governance, adoption, evaluation-branch]
applies_to:
  - GOAL.md
  - docs/AI_FLOW.md
  - AGENTS.md
  - docs/lithos-adoption-manifest.json
---

## When to apply

When evaluating whether to adopt a governance model (here, Lithos full-lifecycle
governance) on an existing product repository, and you must keep product runtime
behavior and product tests untouched while still landing the *complete* model in
concise form.

## What it is

A self-contained evaluation branch worked in an isolated git worktree that adds:

1. An authority chain: `GOAL.md` → `docs/AI_FLOW.md` → the Lithos plan and
   evaluation docs → a machine-readable `docs/lithos-adoption-manifest.json`.
2. The knowledge spine: `docs/dev_log/`, `docs/lessons/`, `docs/practices/`, a
   generated `docs/INDEX.md`, a `docs/lessons/_drift_report.md`, and root
   `LESSONS.md`.
3. Repo-local, standard-library-only tooling under `scripts/`: an index builder,
   a drift signal, a surface-scoped static safety scan, and one aggregating
   governance verifier.
4. Minimal additive edits to existing collaboration files (`AGENTS.md`, the PR
   template) that preserve prior guidance.

Exactly one governance model is used; no minimal/lite/lighter/full adoption
tiers are introduced.

## Why this shape

- Isolation keeps the trial reversible and keeps runtime evidence (the product
  test baseline) valid — the overlay cannot perturb behavior it never touches.
- An authority chain plus a manifest makes the claim auditable by humans and by
  schema, not by trust.
- Standard-library tooling means any contributor or CI runner can reproduce the
  gates with nothing to install.
- A single aggregating verifier gives one command to check the whole surface,
  lowering friction for a small toolkit.

## How to apply

1. Create an isolated worktree on a dedicated branch off `main`.
2. Write the authority chain and the manifest using current single-model Lithos
   language (`governance_model: full-lifecycle-governance`).
3. Add the knowledge spine and seed the indexes (`LESSONS.md`, practices README).
4. Add stdlib tooling; keep every needle/probe fragment-assembled so the
   scanners never match their own source.
5. Run the gates from repo root and record outputs in the dev_log; record the
   pre-adoption product-test baseline as controller-reported, not agent-run.
6. Leave commit/push/PR/merge to the owner/controller; the implementation agent
   only proposes.

## See also

- Originating dev_log: [2026-06-07-lithos-adoption-effects](../dev_log/2026-06-07-lithos-adoption-effects.md)
- Related lesson: [scope the static safety scan](../lessons/2026-06-07-lithos-adoption-effects.md)
- Local workflow: [docs/AI_FLOW.md](../AI_FLOW.md)
