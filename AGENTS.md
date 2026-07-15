# Repository Guidelines

## Project Structure & Module Organization
- Core library code lives in `pypepper/`, grouped by domain: `common/`, `event/`, `fsm/`, `helper/`, `network/`, and `scheduler/`.
- Tests mirror package structure under `tests/` (for example, `pypepper/scheduler/workflow.py` -> `tests/scheduler/test_workflow.py`).
- Runtime/config assets are in `conf/`; local and CI service definitions are in `devenv/`; container build files are in `docker/`.
- Examples are in `example/`, and utility/build scripts are in `scripts/`.

## Build, Test, and Development Commands
- `make build-prepare`: clean output and install dev dependencies.
- `make lint`: run `ruff check`, `ruff format --check`, and `mypy` on `pypepper/`.
- `make check`: run `make lint` plus `scripts/check_mutable_class_attrs.py`.
- `make test`: run `make check` then `pytest --cov=pypepper tests/` with cache cleared (default local validation).
- `make docs` / `make docs-serve`: build or preview the MkDocs Material site (`mkdocs build --strict`). Published at https://jovijovi.github.io/pypepper/ (GitHub Pages from `main`).
- `make build`: install runtime deps, run `scripts/build.py`, and emit `dist/git.json` version metadata.
- `make docker`: build and tag a local Docker image (`pypepper:latest` plus versioned tag).
- `make clean`: remove `dist/`, `.pytest_cache`, and `.coverage`.
- CI runs a dedicated lint/docs job first; the test matrix uses `docker compose -f devenv/ci.yaml up -d` for service-backed cases.

## Coding Style & Naming Conventions
- Target Python `>=3.10, <=3.14`; use 4-space indentation and PEP 8 style.
- Prefer explicit type hints and concise docstrings for public classes/functions.
- Use `snake_case` for modules, functions, and test files; `PascalCase` for classes; constants in `UPPER_SNAKE_CASE`.
- Keep imports package-qualified (for example, `from pypepper.common...`).
- **Do not** declare mutable instance state as class attributes (`_store = {}`, `_lock = Lock()`). Initialize dicts/lists/locks in `__init__` or `__new__`.
- Global registries (`dispatcher`, `connection_manager`, `loader`, channel `manager`) must be **explicit singletons** (module-level instance and/or `__new__`), never accidental shared class dicts.
- Run `python scripts/check_mutable_class_attrs.py` (also via `make check` / `make test`) before opening a PR.
- **Do not** declare mutable instance state as class attributes (`_store = {}`, `_lock = Lock()`). Initialize dicts/lists/locks in `__init__` or `__new__`.
- Global registries (`dispatcher`, `connection_manager`, `loader`, channel `manager`) must be **explicit singletons** (module-level instance and/or `__new__`), never accidental shared class dicts.
- Run `python scripts/check_mutable_class_attrs.py` (also via `make check` / `make test`) before opening a PR.

## Scheduler persistence semantics
Job snapshots (`JobRecord`) are metadata-only (workflows/executors are not serialized). Treat side effects as the source of truth when deciding rollback vs keep-terminal:

| Stage | Persist failure | Required behavior |
|-------|-----------------|-------------------|
| Pre-execution (`INIT`/`SCHEDULE` in `dispatch`) | `save()` fails before enqueue | **Roll back** FSM/`Job.status` so `scheduled()` can retry |
| Pre-execution (channel enqueue) | Enqueue fails before job lands on channel | **Roll back** FSM/`Job.status`, best-effort **delete** Scheduled row, re-raise. Ghost may remain if delete fails. After successful `send`, do **not** roll back. |
| Start (`RUN`) | Running snapshot fails | Do **not** run workflows; prefer persist `Failed`, else restore pre-`RUN` |
| Terminal success (`COMPLETE`) | Work already finished | **Keep** Completed FSM; retry `job.save()` only — **never** re-run workflows because the terminal write failed |
| Terminal failure (`FAIL`) | Work already failed | **Keep** Failed FSM; retry `job.save()` only |
| `Job.save()` field updates | `put()` raises | Do **not** mutate in-memory `status`/`updated` until `put` succeeds |
| `Job.to_record()` | — | Status comes from the **FSM** (authoritative view); may lead last durable `Job.status` and in-memory `Job.status` after a failed terminal `save` |
| `IJobStore.put` | Upsert by `id` | Must **not** overwrite existing ``created`` (memory/SQL/Mongo) |
| SQL/Mongo job store config | Missing `uri` and discrete fields | Raise `ValueError` with a clear message (not bare `assert`) |
| FSM transitions | Invalid event / transition | Raise; do not `save()` or run workflows |

Schedule/enqueue failures are retry-safe. After work finishes (or fails), store lag means retry `save` only — not automatic redelivery. Prefer idempotent executors if callers manually re-dispatch in-flight jobs after a crash.

## Testing Guidelines
- Test framework: `pytest` with `pytest-cov` (`pytest.ini` enforces `testpaths = tests` and `python_files = test_*.py`).
- Place tests in the matching domain folder and name files/functions descriptively (`test_<unit>_<behavior>`).
- Add regression coverage for every bug fix and include edge-case assertions.
- Run `make test` before opening a PR.

## Commit & Pull Request Guidelines
- Commit messages MUST follow Conventional Commits 1.0.0: `https://www.conventionalcommits.org/en/v1.0.0/`.
- Do not create non-conforming commit messages; use types such as `feat`, `fix`, `docs`, `build`, `test`, with optional scope (for example, `feat(network/http): add sse`).
- Keep subjects imperative and scoped (example: `feat(network/http): add sse`).
- Use `.github/pull_request_template.md`: provide problem/fix summary, scope, linked issue, security impact, repro steps, and evidence.
- Include human verification notes and clearly state any unverified areas.
