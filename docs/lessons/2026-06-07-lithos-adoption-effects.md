---
title: "Scope the static safety scan to the governance surface, not the whole product repo"
status: active
created_at: 2026-06-07
last_validated_at: 2026-06-07T00:16:00Z
description: "A repo-wide static safety scan trips on legitimate pre-existing product files; default it to the adoption surface and report the broader-scan limitation honestly."
dev_log: docs/dev_log/2026-06-07-lithos-adoption-effects.md
tags: [lithos, governance, static-safety-scan, verification]
applies_to:
  - scripts/static_safety_scan.py
  - scripts/verify_lithos_adoption.py
  - docs/lithos/adoption-evaluation.md
---

## Symptom

A static safety scan pointed at the entire PyPepper tree reports findings that
have nothing to do with the change under review: cryptographic test vectors that
match secret/key shapes, and legacy task markers in product code. The gate looks
red, but the adoption diff is clean. Contributors are tempted to relax the
scanner's rules to silence the noise.

## Why it happens

PyPepper predates the governance overlay. Its product tree under `pypepper/` and
`tests/` legitimately contains values a heuristic, shape-based scanner flags
(for example, key-shaped fixtures for `common.security.crypto`). The evaluation
branch governs only the artifacts it adds — it explicitly does not change
runtime code or product tests. Scanning everything conflates "is this adoption
surface safe" with "is the whole legacy repo clean", which are different
questions with different owners.

## Rule

Default the static safety scan to the **adoption surface**: the governance docs,
the scripts added by the adoption, and the governance-touched files. Provide an
opt-in `--all` flag for a whole-repo sweep, and state plainly in the scanner
output and in `docs/lithos/adoption-evaluation.md` that the default scope is the
adoption surface. Keep all three required classes (secret-shaped tokens, private
machine paths, unfinished-work placeholders) — narrow the *scope*, never the
*rules*.

## Don't

- Don't claim the gate passes repo-wide when only the surface was scanned.
- Don't drop or weaken any of the three required reject-classes to quiet
  pre-existing product artifacts.
- Don't store secret-shaped or private-path literals in the scanner; assemble
  every needle and self-test probe from fragments at runtime.

## See also

- Originating dev_log: [2026-06-07-lithos-adoption-effects](../dev_log/2026-06-07-lithos-adoption-effects.md)
- Scanner: `scripts/static_safety_scan.py`
- Aggregating verifier: `scripts/verify_lithos_adoption.py`
