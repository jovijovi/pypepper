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
make test    # check + pytest with coverage
```

DB-backed helper tests expect services from `devenv/ci.yaml` on localhost:

```shell
docker compose -f devenv/ci.yaml up -d --wait
make test
```

## Run examples

### HTTP server

```shell
python example/server/app.py --config ./conf/app.config.yaml
```

Default HTTP port comes from `conf/app.config.yaml` (`network.httpServer.port`, typically `55550`).

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

## Documentation site

Online: <https://jovijovi.github.io/pypepper/>

Local preview (same content as the published site):

```shell
make docs        # mkdocs build --strict
make docs-serve  # local preview
```

Push to `main` deploys the site via GitHub Pages (`.github/workflows/docs.yml`).

## Next steps

- Read [Architecture](architecture.md) for module boundaries
- Follow a domain guide under **Guides**
- Optional: enable [Tracing](guides/tracing.md) (console and/or local Jaeger)
