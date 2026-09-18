# Contributing to PyPepper

Thanks for helping improve PyPepper. This note covers the day-to-day path for
code and docs contributions.

## Security vulnerabilities

Do **not** open a public issue for security-sensitive reports. Follow
[`SECURITY.md`](SECURITY.md) (GitHub Security Advisories).

## Development setup

```shell
make build-prepare   # clean + install requirements-dev.txt
make check           # ruff + mypy + mutable class-attr guard
make test            # check + pytest with coverage (>= 90%)
```

Local and CI use branch coverage; Codecov project/patch status is relative to the PR base with a 1% threshold (`codecov.yml`).

DB-backed tests need services from `devenv/ci.yaml`. When those ports are down,
tests marked `requires_postgres` / `requires_mysql` / `requires_mongodb` skip.
Set `PYPEPPER_REQUIRE_DEVENV=1` to fail instead of skip (CI and tag pretest set this).

```shell
docker compose -f devenv/ci.yaml up -d --wait
make test
```

Optional supply-chain check (also runs in the CI lint job):

```shell
make audit           # pip-audit==2.10.1 on requirements.txt and locked uv.lock (uv required)
```

Ignored vulns (if any) live in [`.pip-audit-ignore.txt`](.pip-audit-ignore.txt)
with a reason — prefer upgrading instead of ignoring. The lock pass uses
`uv export --locked`, strips environment markers, and runs pip-audit with
`--disable-pip --no-deps --strict` so the host Python/OS does not drop lock
entries Dependabot still reports.

Docs:

```shell
make docs            # mkdocs build --strict
make docs-serve      # local preview
```

## Pull requests

1. Branch from `main` (for example `feat/...` or `fix/...`).
2. Keep the change focused; match existing package layout under `pypepper/` and
   mirrored tests under `tests/`.
3. Commit messages must follow
   [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
   (for example `feat(scheduler): add cancel`).
4. Fill out [`.github/pull_request_template.md`](.github/pull_request_template.md):
   problem/fix, scope, security impact, repro, and evidence.
5. Run `make check` and `make test` before opening the PR.

## Style

- Python `>=3.10, <=3.14`; 4-space indent; PEP 8; explicit type hints on public APIs.
- Package-qualified imports (`from pypepper.common...`).
- Do not declare mutable instance state as class attributes; initialize in
  `__init__` / `__new__` (see `scripts/check_mutable_class_attrs.py`).

## Questions

Use GitHub Discussions or open an issue with the templates under
[`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/).
