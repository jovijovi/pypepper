---
title: "Lithos adoption effects evaluation plan"
status: active
created_at: 2026-06-07
last_validated_at: 2026-06-07
---
# Lithos Adoption Effects Evaluation Plan

## Purpose

Evaluate how applying Lithos changes PyPepper's development workflow, evidence quality, and agent collaboration without changing product runtime behavior.

This branch is an evaluation branch, not a release or production rollout.

## Branch

- Repository: `jovijovi/pypepper`
- Branch: `test/lithos-adoption-effects`
- Baseline: `origin/main` at the time the branch was created

## AGENT role split

- Hermes: PM/controller, worktree and GitHub operations, scope control, verification, evidence arbitration, final reporting.
- Claude Code: documentation engineer / implementation worker for the Lithos adoption artifacts, using Opus with high reasoning effort and a generous turn budget.
- Codex CLI: independent primary reviewer/evaluator of the branch, blockers, and claimed effects.

## Non-approvals

This branch does not approve:

- runtime behavior changes to `pypepper/`;
- public ingress, hosted services, production config, release/tag/publish actions;
- secret handling changes or external delivery;
- automatic merge after PR creation.

If behavior-bearing code changes become necessary, they must be separately justified and explicitly approved.

## Evaluation question

Does a concise complete Lithos adoption make PyPepper easier and safer for AI-assisted development while keeping project work lightweight enough for a small Python toolkit?

## Effects to evaluate

1. **Authority and scope effect**
   - Clear project goal, local AI-collaboration workflow, approval gates, and non-approvals.
   - Agents should know where to look before making changes.

2. **Verification effect**
   - Existing test command remains real and runnable.
   - Added Lithos verifier should check governance artifacts without replacing product tests.

3. **Knowledge-retention effect**
   - Dev logs, lessons, practices, generated docs index, and drift checks should preserve reusable learning without bloating README or chat history.

4. **Safety and release-boundary effect**
   - Static safety scan and PR checklist should make secrets/private paths/placeholders and release assumptions visible.
   - Safety scan is not behavior evidence.

5. **Agent-collaboration effect**
   - `AGENTS.md` should route Claude Code and Codex roles clearly.
   - The branch should preserve Hermes / Claude Code / Codex responsibility separation.

6. **Friction effect**
   - Added structure should be concise enough for PyPepper and should avoid reintroducing minimal/lite/lighter-vs-full conformance tiers.

## Expected implementation artifacts

Claude Code should inspect Lithos and PyPepper authority files, then add or update concise full-lifecycle governance artifacts as appropriate, likely including:

- `GOAL.md`
- `docs/AI_FLOW.md` or an equivalent local AI-collaboration workflow document
- `docs/lithos/adoption-evaluation.md`
- `docs/lithos-adoption-manifest.json` or equivalent manifest aligned with current Lithos single-model language
- `docs/dev_log/`, `docs/lessons/`, `docs/practices/`, and `docs/INDEX.md`
- repo-local verification tooling for governance docs and safety scan
- PR checklist updates if useful
- `AGENTS.md` updates that preserve PyPepper's existing guidance and add Lithos-specific routing

The exact file names may differ if Claude Code finds a better repo-local convention, but the complete lifecycle structure must remain present in concise form.

## Acceptance gates

- Baseline product tests recorded before adoption.
- Post-adoption product tests still pass.
- New governance verifier passes.
- Static safety scan passes on the intended default adoption surface and reports any intentionally broader scan limitations honestly.
- User-facing documented commands are real and run from the documented directory.
- `git diff --check` passes.
- Python scripts compile.
- Worktree-local CodeGraph is initialized/synced and up to date.
- Codex CLI independent review returns `VERDICT: PASS` with `BLOCKERS: None`, or blockers are fixed and re-reviewed.
- PR, if opened, should be Draft unless the user explicitly approves ready-for-review.

## Reporting

Final report should be compact and evidence-based:

- branch / PR state;
- what Lithos artifacts were added;
- which effects improved, which remain uncertain;
- verification results;
- Codex verdict;
- any tails or explicit non-approvals.
