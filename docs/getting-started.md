# Getting Started

## Requirements

- Python `3.10`–`3.14`
- [uv](https://github.com/astral-sh/uv) `>= 0.10.7` (recommended for local installs)
- Docker (optional; required for DB helper integration tests)

## Install

```shell
make build-prepare
```

This cleans build output and installs development dependencies from `requirements-dev.txt`.

For runtime-only dependencies:

```shell
uv pip install -r requirements.txt
```

## Validate locally

```shell
make lint    # ruff + mypy on pypepper/
make check   # lint + mutable class-attr guard
make test    # check + pytest with coverage (>= 90%; branch coverage enabled)
```

Local and CI upload branch coverage (`branch = true`). Codecov project compares overall coverage vs the PR base; patch compares changed lines vs an auto target; both allow a 1% threshold.

DB-backed helper tests expect services from `devenv/ci.yaml` on localhost:

```shell
docker compose -f devenv/ci.yaml up -d --wait
make test
```

## Run examples

Prefer curated domain imports in application code:

```python
from pypepper.common.config import config
from pypepper.scheduler import Job, setup_from_config

config.load_config("./conf/app.config.yaml")
# Durable scheduler.jobStore backends are not applied by load_config alone:
setup_from_config(config.get_yml_config())
```

For a guided walkthrough (expected COMPLETE output and common pitfalls), see
[Tutorial: First service](tutorials/first-service.md).

### HTTP server

```shell
python example/server/app.py --config ./conf/app.config.yaml
```

Default HTTP port comes from `conf/app.config.yaml` (`network.httpServer.port`, typically `55550`).
The example calls `setup_from_config` after `load_config`.

### Scheduler example

```shell
python example/scheduler/app.py
```

Runs `load_config` → `setup_from_config` → `Job.scheduled` → `Worker` through COMPLETE.
See [Scheduler](guides/scheduler.md).

### SSE example

Inject a local API key (config ships with empty `validKeys`):

```shell
export PYPEPPER_SSE_API_KEY=your-local-key
python example/sse/app.py
```

Connect:

```shell
curl -N -H "X-API-Key: $PYPEPPER_SSE_API_KEY" http://localhost:55550/sse/echo
```

Keep `sse.authentication.enabled: true` for anything beyond local experiments.
To temporarily allow auth-off locally, export `PYPEPPER_SSE_ALLOW_AUTH_OFF=1`
(see [SSE security notes](guides/network-sse.md#security-notes)).

## Documentation site

Online: <https://jovijovi.github.io/pypepper/>

Local preview (same content as the published site):

```shell
make docs        # mkdocs build --strict
make docs-serve  # local preview
```

Push to `main` deploys the site via GitHub Pages (`.github/workflows/docs.yml`).

## Release

Tag-triggered PyPI publishing: see [Release](guides/release.md).

Summary: bump `version` in `pyproject.toml`, merge to `main`, then `git tag vX.Y.Z && git push origin vX.Y.Z` (tag must match the pyproject version). Configure PyPI Trusted Publisher once as described in that guide.

## Next steps

- Read [Architecture](architecture.md) for module boundaries
- Follow a domain guide under **Guides**
- Browse the [API Reference](reference/index.md) for signatures and types
- Optional: enable [Tracing](guides/tracing.md) (console and/or local Jaeger)
- Maintainers: [Release](guides/release.md) to PyPI via Git tag
