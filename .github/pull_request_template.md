## Summary

Describe the problem and fix in 2–5 bullets:

- Problem:
- Why it matters:
- What changed:
- What did NOT change (scope boundary):

## Change Type (select all)

- [ ] Bug fix
- [ ] Feature
- [ ] Refactor
- [ ] Docs
- [ ] Security hardening
- [ ] Chore/infra

## Scope (select all touched areas)

- [ ] common
- [ ] event
- [ ] fsm
- [ ] helper
- [ ] network
- [ ] scheduler
- [ ] CI/CD / infra

## Linked Issue/PR

- Closes #
- Related #

## User-visible / Behavior Changes

List user-visible changes (including defaults/config).  
If none, write `None`.

## Security Impact (required)

- New permissions/capabilities? (`Yes/No`)
- Secrets/tokens handling changed? (`Yes/No`)
- New/changed network calls? (`Yes/No`)
- Command/tool execution surface changed? (`Yes/No`)
- Data access scope changed? (`Yes/No`)
- If any `Yes`, explain risk + mitigation:

## Repro + Verification

### Environment

- OS:
- Runtime/container:
- Relevant config (redacted):

### Steps

1.
2.
3.

### Expected

-

### Actual

-

## Evidence

Attach at least one:

- [ ] Failing test/log before + passing after
- [ ] Trace/log snippets
- [ ] Screenshot/recording
- [ ] Perf numbers (if relevant)

## Lithos Adoption Gates

This repository follows Lithos (see [`docs/AI_FLOW.md`](../docs/AI_FLOW.md)) at the
lighter-governed-workflow depth. Run the local gates from the repo root and report the
result (they are safety/declaration evidence only — they prove no behavior and clear no
approval gate):

- [ ] `make lithos-verify` passes (static safety scan + manifest conformance), or both scripts run individually:
  - [ ] `python3 scripts/verify_static_safety.py`
  - [ ] `python3 scripts/verify_lithos_conformance.py`
- [ ] If governance docs/manifest changed, `docs/AI_FLOW.md`, `docs/lithos/adoption-manifest.json`, and `docs/lithos/evaluation-report.md` remain consistent.

## Human Verification (required)

What you personally verified (not just CI), and how:

- Verified scenarios:
- Edge cases checked:
- What you did **not** verify:

## Compatibility / Migration

- Backward compatible? (`Yes/No`)
- Config/env changes? (`Yes/No`)
- Migration needed? (`Yes/No`)
- If yes, exact upgrade steps:

## Failure Recovery (if this breaks)

- How to disable/revert this change quickly:
- Files/config to restore:
- Known bad symptoms reviewers should watch for:

## Risks and Mitigations

List only real risks for this PR. Add/remove entries as needed. If none, write `None`.

- Risk:
  - Mitigation:
