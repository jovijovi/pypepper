# Goal — PyPepper Lithos adoption/effects evaluation

## Goal

Evaluate how adopting the Lithos **full-lifecycle governance** model changes
PyPepper's AI-assisted development workflow, evidence quality, and agent
collaboration — **without changing any product runtime behavior**. This is an
evaluation branch (`test/lithos-adoption-effects`), not a release or a
production rollout.

The branch answers one question: does a concise, complete full-lifecycle
governance surface make PyPepper easier and safer for AI-assisted development
while staying light enough for a small Python toolkit?

## In scope

- Governance authority docs (`GOAL.md`, `docs/AI_FLOW.md`).
- Lithos adoption artifacts (`docs/lithos/`, `docs/lithos-adoption-manifest.json`).
- The knowledge spine (`docs/dev_log/`, `docs/lessons/`, `docs/practices/`,
  `docs/INDEX.md`, `docs/lessons/_drift_report.md`, root `LESSONS.md`).
- Repo-local governance tooling under `scripts/`.
- Minimal, additive edits to `AGENTS.md` and `.github/pull_request_template.md`.

## Boundaries

- No runtime behavior changes to `pypepper/`.
- No edits to product tests under `tests/`.
- No new third-party dependencies; governance scripts are Python standard
  library only.
- No private machine paths, secrets, tokens, API keys, or private keys in any
  committed text. Committed paths are repository-relative.
- One governance model only: Lithos full-lifecycle governance. No
  minimal/lite/lighter/full adoption tiers or profiles are introduced.

## Non-approvals

This branch does **not** approve, and the implementation agent did **not**
perform, any of the following:

- runtime behavior changes to `pypepper/`;
- commit, push, merge, branch deletion, or release/publish/tag actions;
- opening or auto-merging pull requests;
- public ingress, hosted services, production config, or live/runtime defaults;
- secret handling changes or external delivery.

If behavior-bearing code changes ever become necessary, they must be separately
justified and explicitly approved by the human owner.

## Document authority chain

`GOAL.md` (this file) → `docs/AI_FLOW.md` (local AI-collaboration workflow) →
`docs/lithos/evaluation-plan.md` (what to evaluate) →
`docs/lithos/adoption-evaluation.md` (effects + evidence) →
`docs/lithos-adoption-manifest.json` (machine-readable conformance claim).
