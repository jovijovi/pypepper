# Lessons learned

Pitfalls discovered while working on this codebase. Add an entry here when a
future change made without this knowledge would repeat the same mistake. The
detailed lesson lives at `docs/lessons/YYYY-MM-DD-<topic>.md`; reusable patterns
live under `docs/practices/` (index: `docs/practices/README.md`). The generated
catalogue of all knowledge docs is `docs/INDEX.md`.

When a commit, PR, or dev_log cites a lesson or practice, re-validate the cited
file's frontmatter (use-driven validation): bump `last_validated_at`, refine the
body, or deprecate it.

## Governance / Lithos adoption

- [Scope the static safety scan to the governance surface, not the whole product repo](docs/lessons/2026-06-07-lithos-adoption-effects.md) — default to the adoption surface; offer `--all`; report the limitation honestly.
