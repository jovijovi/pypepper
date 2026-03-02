# Repository Guidelines

## Project Structure & Module Organization
- Core library code lives in `pypepper/`, grouped by domain: `common/`, `event/`, `fsm/`, `helper/`, `network/`, and `scheduler/`.
- Tests mirror package structure under `tests/` (for example, `pypepper/scheduler/workflow.py` -> `tests/scheduler/test_workflow.py`).
- Runtime/config assets are in `conf/`; local and CI service definitions are in `devenv/`; container build files are in `docker/`.
- Examples are in `example/`, and utility/build scripts are in `scripts/`.

## Build, Test, and Development Commands
- `make build-prepare`: clean output and install dev dependencies.
- `make test`: run `pytest --cov=pypepper tests/` with cache cleared (default local validation).
- `make build`: install runtime deps, run `scripts/build.py`, and emit `dist/git.json` version metadata.
- `make docker`: build and tag a local Docker image (`pypepper:latest` plus versioned tag).
- `make clean`: remove `dist/`, `.pytest_cache`, and `.coverage`.
- CI also uses `docker compose -f devenv/ci.yaml up -d` before tests for service-backed cases.

## Coding Style & Naming Conventions
- Target Python `>=3.10, <=3.14`; use 4-space indentation and PEP 8 style.
- Prefer explicit type hints and concise docstrings for public classes/functions.
- Use `snake_case` for modules, functions, and test files; `PascalCase` for classes; constants in `UPPER_SNAKE_CASE`.
- Keep imports package-qualified (for example, `from pypepper.common...`).

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
