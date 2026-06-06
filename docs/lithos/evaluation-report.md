# Lithos Adoption Evaluation Report — PyPepper

**Branch:** `test/lithos-adoption-evaluation`

**Scope of this report.** This document records what applying
[Lithos](https://github.com/jovijovi/lithos) to PyPepper actually produced on
this branch: the adoption depth chosen and why, the observed effects and
friction, exactly what the local gates do and do not cover, and the conformance
gaps that remain. It is the honest companion to the conformance *claim* made in
[`adoption-manifest.json`](adoption-manifest.json) and the workflow contract in
[`../AI_FLOW.md`](../AI_FLOW.md): the manifest declares, this report qualifies.

Nothing here authorizes anything. A clean gate is evidence, not permission; see
"What the gates do not prove" below.

## What was evaluated

The goal was to test whether Lithos improves PyPepper's human–AI collaboration
**without changing runtime behavior**. No file under `pypepper/` was modified.
The experiment is therefore a *governance-surface* adoption: it adds documents,
a machine-readable manifest, and two pure-standard-library verification scripts,
and measures the value and the friction of that surface.

## Adoption depth and why

PyPepper adopts the **lighter governed workflow** depth, not the full governed
project. The reasoning:

- PyPepper is a single-maintainer library/toolkit consumed as a dependency. It
  does not operate a live service as part of this repository's governed work, so
  the runtime gate is out of scope (while never weakened — see the manifest's
  `live_runtime` gate and `../AI_FLOW.md`).
- Lithos requires that even the lighter depth preserve roles, the four-gate
  layering, worktree/branch isolation, and evidence-based verification. Those are
  all present, so the adoption is genuinely Lithos rather than a thinned-out
  imitation.
- The full governed project depth adds a knowledge spine (dev logs, lessons,
  practices, generated index, drift report) and scenario-regression fixtures.
  Those are valuable for larger, multi-agent, or behavior-bearing programs; for a
  single-maintainer library they would be ceremony without a matching risk to
  govern. Choosing the lighter depth is the smallest truthful adoption that still
  demonstrates value, which is exactly what the standard's `local-adoption.md`
  recommends.

This choice is the most important honesty boundary in the experiment: the branch
does **not** claim full governed project conformance, and the manifest declares
`lighter-governed-workflow` so a reader (or the conformance checker) cannot
mistake the depth.

## What was added (the adoption surface)

| Artifact | Role |
| --- | --- |
| [`../AI_FLOW.md`](../AI_FLOW.md) | The single local workflow file: roles, four approval gates, working discipline, environment/sandbox boundaries, definition of done. |
| [`adoption-manifest.json`](adoption-manifest.json) | Machine-readable conformance declaration (version, depth, roles, gates, autonomous-PR policy). |
| [`../../scripts/verify_lithos_conformance.py`](../../scripts/verify_lithos_conformance.py) | Validates the manifest against the governance invariants and checks that the named workflow file exists. |
| [`../../scripts/verify_static_safety.py`](../../scripts/verify_static_safety.py) | Static safety scan over the governed text surface: rejects secret-shaped tokens, private machine-local paths, and unfinished-work markers. |
| `make lithos-verify` | Convenience target that runs both gates from the repository root. |
| References in `README.md`, `AGENTS.md`, `.github/pull_request_template.md` | Make the workflow discoverable from the project's entry points, as Lithos requires. |

## Effects and benefits observed

- **One discoverable source of truth.** Before adoption, collaboration rules
  were implicit and split between `CLAUDE.md`/`AGENTS.md` boilerplate. The
  workflow file now states the roles, gates, and definition of done in one place,
  reachable from the README, the agent contract, and the PR template.
- **Machine-checkable governance.** The manifest turns "we follow Lithos" from a
  prose assertion into a declaration a script validates. The conformance checker
  self-tests its own invariants on a known-good manifest before validating the
  real one, so a green result means the engine works rather than that it matched
  nothing.
- **Mechanical safety floor.** The static safety scan catches the most damaging,
  mechanically detectable mistakes — a leaked credential shape, a hard-coded home
  directory, an unfinished-work marker — in committed text, before review. It,
  too, self-tests on runtime-built probes.
- **Low intrusion.** The entire adoption is documents and two dependency-free
  scripts. It changes no runtime code, adds no third-party dependency, and the
  gates run from a clean checkout with only the standard library.
- **Clear escalation language.** The four-gate model gives contributors and
  agents a shared vocabulary for "this needs the owner" (merge, release,
  destructive/external, live/runtime), reducing the chance an agent quietly does
  something that should have been escalated.

## Friction encountered

- **`make test` vs. environment `pytest`.** During baseline verification,
  `make test` initially failed because the shell resolved `pytest` to a
  user-local install whose plugin set did not expose `--cov`. Running
  `python3 -m pytest` in the active environment passed. This is an environment
  PATH issue, not a Lithos issue, but it is worth recording: a governed
  "definition of done" is only as reproducible as the toolchain behind it.
- **No-self-match constraint.** Because the static safety scan reads committed
  text including its own source, every sensitive pattern and probe must be
  assembled from split fragments so the scanner never flags itself. This is the
  correct design, but it makes the scripts (and any prose that discusses marker
  literals) less obvious to a casual reader.
- **Scope discipline around the runtime tree.** The pre-existing `pypepper/`
  source carries long-standing legacy task-marker comments, and the wider tree
  contains benign strings (local-dev `root` connection usernames, a container
  build-cache path, `private`/`key` identifiers) that trip the scanner's
  deliberately conservative heuristics. Rewriting source or allowlisting matches
  is out of scope for a behavior-neutral evaluation branch, so the default scan
  covers the adoption surface only. Keeping that narrowing *honest* (rather than a
  hidden exemption) required the explicit `--all` mode and the gap note below.
- **Prose/manifest/script agreement is manual.** The conformance checker
  validates the manifest's internal consistency and that the workflow file
  exists, but it does not verify that the *prose* in the workflow file, the
  manifest, and this report all agree. Keeping them aligned is a human
  responsibility (and a thing the independent reviewer should check).

## What the gates cover — and what they do not

**The static safety scan covers**, by default, the governed adoption surface
listed in `verify_static_safety.py` (`GOVERNED_SURFACE`): `docs/AI_FLOW.md`,
everything under `docs/lithos/`, `AGENTS.md`, `README.md`, the PR template, and
the two scripts. Within whatever paths it scans, it always enforces all three
finding classes — narrowing the *paths* never drops a *finding class*.

**The static safety scan does not cover**, by default, the `pypepper/` runtime
tree, tests, examples, or build/CI configuration. Those are reachable with
`python3 scripts/verify_static_safety.py --all`, which scans every text file. On
this branch `--all` exits non-zero and reports a mix worth understanding:

- **Real legacy markers** — long-standing unfinished-work comments in several
  `pypepper/` runtime modules. These are genuine findings the evaluation branch
  deliberately does not rewrite, because editing runtime source would not be
  behavior-neutral.
- **Heuristic false positives** — the scan is documented to err toward flagging,
  and over the wider tree that shows. Local-development database connection URLs
  whose username component is the throwaway `root` account (in a compose file and
  a test fixture) and the standard container build-cache directory under the root
  account's home in the Dockerfile (a portable, intentional path, not a
  contributor's machine) both match the private-path shape; and identifiers and
  type annotations built from the words *private* and *key* in the crypto module
  and its test match the secret-key shape without being secrets.

That `--all` output is expected and is the honest, demonstrable form of this gap —
not a regression. It also explains *why* the governed surface is scoped narrowly:
bringing the runtime tree under the gate would require either source changes or a
reviewed allowlist for the benign matches, which is out of scope here.

**The conformance checker covers** the manifest's governance invariants (roles,
gate layering, owner-approval authority, autonomous-PR policy, secret/private-path
cleanliness of the manifest itself) and the existence of the named workflow file.
It does **not** check prose consistency across documents, nor does it validate
the full upstream JSON Schema with a schema library (it is a focused
standard-library checker for this one manifest).

## Remaining conformance gaps

1. **Gates are local-only, not yet a required CI check.** The repository's
   GitHub Actions `Test` workflow runs `make test` (pytest + coverage) across the
   supported Python matrix; it does **not** yet run `make lithos-verify`. Wiring
   the static safety scan and conformance check as required CI checks is the
   recommended next step so the gates cannot be skipped by forgetting to run them
   locally. Until then, a contributor or reviewer must run them by hand and report
   the result.
2. **Runtime tree is outside the default scan.** `pypepper/` (and tests,
   examples, devenv, docker) are not scanned by default. `--all` shows what
   bringing them in would surface: real legacy unfinished-work markers in the
   runtime modules plus heuristic false positives (detailed under "What the gates
   cover" above). Closing this gap is a separate, behavior-aware change — it needs
   either source edits or a reviewed allowlist for the benign matches — and is
   intentionally outside this behavior-neutral evaluation branch's scope.
3. **No knowledge spine or scenario-regression fixtures.** These are
   full-governed-project features and are deliberately not claimed at the lighter
   depth. If PyPepper later grows multi-agent or behavior-governing needs, the
   governed-upgrade path would add them.
4. **Cross-document agreement is human-maintained.** Nothing mechanically proves
   that the workflow file, the manifest, and this report stay in sync; that is the
   reviewer's job.

## Verification evidence

All gates are pure standard library and run from the repository root. They are
reproducible — re-run them to regenerate the result rather than trusting this
text:

```shell
python3 scripts/verify_static_safety.py        # static safety scan (adoption surface)
python3 scripts/verify_static_safety.py --all  # whole repo; reports legacy runtime markers
python3 scripts/verify_lithos_conformance.py   # validate the adoption manifest
make lithos-verify                             # runs both gates together
```

On this branch, the default static safety scan and the conformance checker both
pass (each after self-testing its own engine), and `make lithos-verify` exits
zero. The `--all` scan exits non-zero and reports pre-existing findings — both
real legacy markers and heuristic false positives — as detailed under "What the
gates cover" above; that is the intended, honest demonstration of gap (2), not a
regression. The runtime test suite is verified separately via `make test` / the
CI `Test` workflow and is independent of these governance gates.

## What the gates do not prove

The static safety scan is **safety evidence only**. A clean scan proves that the
scanned text is free of secret-shaped tokens, private machine-local paths, and
unfinished-work markers; it proves **nothing about behavior**. Behavior is proven
by tests, not by a clean scan. Likewise, the conformance checker proves the
manifest is a well-formed, internally consistent conformance *declaration* — it
authorizes nothing and clears no approval gate. Merge, release, destructive or
external actions, and any live/runtime work remain with the human owner under the
gates described in `../AI_FLOW.md`.

## Recommendation

For a single-maintainer library, the lighter governed workflow is a good fit: it
adds a real, machine-checked safety and governance floor at low cost and with no
runtime risk. The highest-value follow-up is wiring the two gates into CI as
required checks (gap 1); the runtime-tree marker cleanup (gap 2) is worthwhile but
should be done as its own behavior-aware change, not folded into this
behavior-neutral evaluation branch.
