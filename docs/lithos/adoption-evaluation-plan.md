# Lithos Adoption Evaluation Plan for PyPepper

**Branch:** `test/lithos-adoption-evaluation`

**Goal:** test and evaluate the effect of applying Lithos to PyPepper without changing runtime behavior or publishing/releasing anything.

**Owner instruction:** create a dedicated branch in `jovijovi/pypepper` for Lithos application testing/evaluation. Claude Code and Codex CLI must both participate, with Hermes as controller/verifier.

## AGENT role split

- **Hermes:** project manager/controller, branch/worktree setup, scope control, deterministic verification, GitHub operations, and final evidence arbitration.
- **Claude Code:** documentation engineer / implementation worker for the Lithos adoption experiment, using generous max-turn budget.
- **Codex CLI:** independent primary reviewer/evaluator; it must challenge whether the branch truthfully applies Lithos and whether the claimed effects are supported by evidence.

## Approved scope

This branch may add or adjust documentation, governance templates, local verification scripts, manifests, and PR/checklist guidance needed to test Lithos adoption on PyPepper.

## Explicit non-approvals

- No merge to `main` unless separately approved.
- No release/tag/package publish.
- No production/live/runtime behavior changes.
- No secrets, credentials, private machine-local paths, or private internal system names in committed artifacts.
- No force push, branch deletion, or history rewrite.

## Expected adoption/evaluation artifacts

Claude Code should inspect the repository and choose the smallest truthful Lithos adoption depth that can demonstrate value. Prefer a lighter governed workflow unless evidence shows full governed project adoption is justified for this evaluation branch.

Candidate artifacts:

- a local Lithos workflow file, likely `docs/AI_FLOW.md` or another clearly named project workflow document;
- an adoption manifest or evaluation manifest that describes the branch's Lithos depth and limits;
- a static safety scan or equivalent local safety gate if feasible;
- README / AGENTS / PR-template references if needed for discoverability;
- an evaluation report explaining the effects, benefits, friction, and remaining conformance gaps.

## Verification baseline already established

- Repository: `jovijovi/pypepper`
- Default branch: `main`
- Starting commit: `c35568bcc3da7043f56633c32abc93a1382de8dc`
- Worktree: a dedicated git worktree checked out on `test/lithos-adoption-evaluation` (absolute machine-local path intentionally omitted to keep this artifact portable and free of private paths).
- CodeGraph: initialized and up to date in this worktree.
- Baseline tests: `python3 -m pytest --cov=pypepper tests/` passed with Docker compose services from `devenv/ci.yaml`; 106 tests passed.
- Caveat: local `make test` initially failed because the shell resolved `pytest` to a user-local `~/.local/bin/pytest`, whose plugin environment did not expose `--cov`; using `python3 -m pytest` in the active Python environment passed. CI's install step may not hit that local PATH issue.

## Acceptance criteria for this branch

1. The branch contains a clear, non-overclaiming Lithos adoption/evaluation surface.
2. Runtime source behavior is not changed unless explicitly justified as a verification-only helper and approved by the plan.
3. Any conformance claim is truthful: prose, manifest, scripts, and documented commands agree.
4. Static safety is treated as safety evidence only, never behavior proof.
5. Claude Code records an implementation/evaluation summary.
6. Codex CLI performs an independent blocker-only evaluation after Claude's changes.
7. Hermes verifies deterministic local gates, CodeGraph freshness, worktree status, and GitHub branch/PR state if pushed/opened.
