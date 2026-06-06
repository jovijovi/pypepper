# AI-Collaborative Development Standards — PyPepper

This project follows the [Lithos](https://github.com/jovijovi/lithos) AI-collaboration
standard (version 1.x) at the **lighter-governed-workflow** depth. This file is the
single source of truth for how humans and AI collaborate on PyPepper, and it is
itself change-controlled.

> Adopting this workflow does **not** authorize live or autonomous AI execution.
> Approvals here are organizational. PyPepper is a library/toolkit and does not
> operate at the live/runtime layer as part of this repository's governed work.

**Status of this adoption.** It was introduced on the `test/lithos-adoption-evaluation`
branch to evaluate whether Lithos improves PyPepper's AI collaboration without changing
runtime behavior. No code under `pypepper/` is modified by the adoption. The companion
[adoption manifest](lithos/adoption-manifest.json) declares the conformance claim, and
[the evaluation report](lithos/evaluation-report.md) records effects, friction, and the
remaining gaps — including which parts of the repository the gates do and do not yet cover.

## Roles

Review and verification are independent of implementation. Approval authority is
human-only and is never held by an implementation agent.

| Role | Held by | Notes |
| --- | --- | --- |
| Owner / approver | The PyPepper maintainer (GitHub: `jovijovi`) | Sole approval authority; human only. |
| Controller / operator | The maintainer, or an orchestrating agent under the maintainer's instruction | Drives sessions and surfaces decisions; does not approve. |
| Architect | The maintainer | Owns design and acceptance criteria. |
| Implementation agent | A contributing engineer or an AI agent (for example, an assistant working in this repo) | Implements within approved scope. |
| Reviewer | A contributor or review agent independent of the implementation | Independent of implementation. |
| Verifier | The GitHub Actions `Test` workflow plus the independent reviewer | Independent; produces reproducible evidence. |

**Combined roles (stated explicitly).** On this small, single-maintainer project the
owner, controller, and architect are typically the same person (the maintainer). That
combination is permitted, but approval authority remains human and is never delegated to
an implementation agent, and the reviewer/verifier must stay independent of whoever
implemented the change.

## Approval gates and how they are signaled

1. **Preparation / preflight** — isolated, reversible work on a feature branch or worktree;
   standing authorization, no shared or external effect. This is the default working mode.
2. **Implementation** — merging to `main` requires the owner's review and sign-off,
   recorded in the GitHub pull request, with the `Test` workflow green across the supported
   Python matrix. Scope is limited to the reviewed change. An agent may open and update its
   own pull request, but must never self-approve, self-merge, or enable ownerless
   auto-merge — merging is the owner's decision.
3. **Destructive / external** — explicit, per-action owner approval, recorded in the pull
   request or tracking issue. Inventory of such actions for this repository:
   - publishing to PyPI or TestPyPI (`make publish`, `make publish-test`);
   - pushing, moving, or deleting git tags or branches; force-push or history rewrite;
   - building and pushing a distributed Docker image to a registry;
   - any use of release or coverage credentials (for example `CODECOV_TOKEN`);
   - sending external communications or mutating any external service.
4. **Live / runtime execution** — **out of scope.** PyPepper is a microservice toolkit
   consumed as a library; this repository's governed work does not operate a live service.
   Even so, the live/runtime gate is never weakened: if that ever changes, it still requires
   explicit owner approval and the separate runtime controls described below.

Clearing one gate never clears a higher one. When it is unclear which gate an action falls
under, treat it as the higher gate and ask.

## Working discipline

- One collaboration unit per branch; branch from `main` as `type/short-description`, with
  `type` drawn from the Conventional Commits set the project already uses (`feat`, `fix`,
  `docs`, `build`, `test`, `chore`).
- Parallel work uses isolated worktrees or checkouts so uncommitted changes never cross units.
- `main` contains only reviewed, verified work and is protected by branch protection; CI must
  be green before merge.

## Environment and sandbox boundaries

This section states *where* a run may execute and *what it may touch*. It describes limits;
it does not grant capability, and it never authorizes live or autonomous execution. A project
may tighten any boundary below; it must not loosen one and still claim conformance.

- **Isolation:** git worktree isolation per unit. There is no OS/process sandbox beyond that
  worktree isolation. A worktree does not sandbox a process; a sandbox does not version changes.
- **Filesystem roots:** writes are confined to the unit's working tree and the build/test
  outputs the project already ignores (`dist/`, `.pytest_cache`, `.coverage`). Reads outside
  the project — a home directory, system configuration, or unrelated repositories — are not
  part of normal collaboration work. Committed text uses repository-relative paths only; no
  private machine-local absolute paths.
- **Network:** egress is **none** for documentation and preparation work. Test and build may
  resolve declared package indexes (PyPI) to install dependencies; in CI, the service-backed
  test cases start the local containers defined in `devenv/ci.yaml` (MongoDB, MySQL,
  PostgreSQL) on the runner. Ingress is **none**. Publishing endpoints (PyPI/TestPyPI, a
  container registry) are reachable only under the destructive/external gate.
- **Credentials:** **none** for preparation and documentation work. Release and coverage
  tokens (PyPI, `CODECOV_TOKEN`) are least-privilege, used only by their specific CI jobs, and
  are never written into the working tree, logs, or any manifest — use a `[REDACTED]`
  placeholder if one must be referenced.
- **Escalation / abort:** on meeting a boundary — an unexpected credential prompt, a write
  outside the declared roots, or any action with an external or live effect — stop and request
  the higher gate rather than working around it.

## Verification — definition of done

A unit is accepted only with reproducible evidence:

- [ ] Tests added or updated and passing; the linked `Test` workflow run is green across the
      supported Python versions.
- [ ] Reproduction steps recorded for any behavioral change.
- [ ] The **static safety scan** passes over the governed surface
      (`python3 scripts/verify_static_safety.py`); it rejects secret-shaped tokens, private
      machine-local paths, and unfinished-work markers. This is **safety evidence only — not
      proof of behavior**; behavior is proven by tests, not by a clean scan.
- [ ] The **adoption manifest** validates
      (`python3 scripts/verify_lithos_conformance.py`).
- [ ] The independent reviewer's concerns are resolved or explicitly accepted by the owner.
- [ ] Failures, skips, and unverified areas are reported faithfully.

### Local gate commands

Run from the repository root (pure standard library, no extra dependencies):

```shell
python3 scripts/verify_static_safety.py        # static safety scan (adoption surface)
python3 scripts/verify_static_safety.py --all  # scan the whole repo (shows out-of-scope findings)
python3 scripts/verify_lithos_conformance.py   # validate the adoption manifest
```

`make lithos-verify` runs both gates together. The static safety scan is currently a **local**
gate; wiring it as a required CI check is the recommended next step and is recorded as a gap
in the [evaluation report](lithos/evaluation-report.md).

## Autonomous PR policy

An agent may open, update, and close its own pull request as preparation, but Lithos adoption
**never** licenses agent self-approval, agent self-merge, ownerless auto-merge, ownerless
branch deletion, or ownerless release/publish. Merging, branch deletion, releasing, and
external communication all require explicit higher-gate owner approval. These same constraints
are declared, machine-readably, in the [adoption manifest](lithos/adoption-manifest.json).

## Runtime controls

PyPepper does not operate at the live/runtime layer in this repository's governed work, so no
runtime controls are claimed here. Standing up a live service would require its own explicit
human authorization, monitoring, kill switch, and audit — Lithos does not provide these, and
this document does not grant them.

## Change control for this document

Normative changes to this file follow [Lithos governance](https://github.com/jovijovi/lithos):
they are reviewed like code, and any companion artifacts (`AGENTS.md`, the PR template, the
adoption manifest, translations) change together in the same pull request.

## Companions

- Agent-facing contract: [`AGENTS.md`](../AGENTS.md).
- PR checklist: [`.github/pull_request_template.md`](../.github/pull_request_template.md).
- Environment and sandbox policy: the "Environment and sandbox boundaries" section above.
- Adoption manifest (the conformance declaration): [`docs/lithos/adoption-manifest.json`](lithos/adoption-manifest.json).
- Local gates: [`scripts/verify_static_safety.py`](../scripts/verify_static_safety.py),
  [`scripts/verify_lithos_conformance.py`](../scripts/verify_lithos_conformance.py).
- Evaluation report: [`docs/lithos/evaluation-report.md`](lithos/evaluation-report.md).
