<div align="center">
  <img src="docs/logo/logo.svg" alt="PyPepper" width="128" />

  <h1>PyPepper</h1>

  <p>
    <strong>Composable building blocks for Python microservices.</strong><br />
    Build faster. Live more.
  </p>

  <p>
    <a href="https://pypi.org/project/pypepper/"><img src="https://img.shields.io/pypi/v/pypepper?style=flat-square&logo=pypi&logoColor=white&label=PyPI" alt="PyPI" /></a>
    <a href="https://jovijovi.github.io/pypepper/"><img src="https://img.shields.io/badge/docs-online-0A7EA4?style=flat-square" alt="Docs" /></a>
    <a href="https://github.com/jovijovi/pypepper/actions"><img src="https://img.shields.io/github/actions/workflow/status/jovijovi/pypepper/test.yaml?branch=main&style=flat-square&label=CI" alt="CI" /></a>
    <a href="https://codecov.io/gh/jovijovi/pypepper"><img src="https://img.shields.io/codecov/c/github/jovijovi/pypepper?style=flat-square&logo=codecov&logoColor=white" alt="Coverage" /></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%E2%80%933.14-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2F2F2F?style=flat-square" alt="License" /></a>
  </p>
</div>

<p align="center"><em>In memory of my father, who passed away in 2023 from COVID-19.</em></p>

---

PyPepper is a small toolkit—not a full framework—for wiring services: **HTTP / SSE**, **FSM**, a **workflow scheduler**, signed **events**, thin **DB helpers**, and optional **OpenTelemetry** tracing. Supports Python `3.10`–`3.14`.

- Repo: [github.com/jovijovi/pypepper](https://github.com/jovijovi/pypepper)
- Docs: [jovijovi.github.io/pypepper](https://jovijovi.github.io/pypepper/)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)

```shell
pip install pypepper
```

## Documentation

[Getting Started](https://jovijovi.github.io/pypepper/getting-started/) · [Tutorial](https://jovijovi.github.io/pypepper/tutorials/first-service/) · [Architecture](https://jovijovi.github.io/pypepper/architecture/) · [Guides](https://jovijovi.github.io/pypepper/guides/common/) · [API Reference](https://jovijovi.github.io/pypepper/reference/)

Source under [`docs/`](docs/index.md). Local preview: `make docs-serve`.

## Domains

| | Package | Role |
|:--|:--|:--|
| **Common** | `pypepper.common` | Config, logging, context, cache, crypto, utilities |
| **Event** | `pypepper.event` | Signed domain events with JSON marshal |
| **FSM** | `pypepper.fsm` | Event-triggered state machine with rollback |
| **Scheduler** | `pypepper.scheduler` | `Job → Channel → Worker → Workflow` + pluggable job stores |
| **Network** | `pypepper.network` | FastAPI HTTP server and SSE subsystem |
| **Helper** | `pypepper.helper` | MySQL / PostgreSQL / MongoDB connectors |

## Highlights

| | |
|:--|:--|
| **Network** | FastAPI HTTP + SSE; header API-key auth and rate limits (auth-off needs `PYPEPPER_SSE_ALLOW_AUTH_OFF`) → [guide](https://jovijovi.github.io/pypepper/guides/network-sse/) |
| **FSM & events** | Rollback on handler failure; signed JSON payloads → [guide](https://jovijovi.github.io/pypepper/guides/event-fsm/) |
| **Scheduler** | Rounds, soft timeouts, and retries; durable job-store fail-fast → [guide](https://jovijovi.github.io/pypepper/guides/scheduler/) |
| **Tracing** | Opt-in OpenTelemetry (console / local Jaeger) → [guide](https://jovijovi.github.io/pypepper/guides/tracing/) |
| **Quality** | PEP 561 `py.typed` · ruff + mypy CI · line + branch coverage `≥ 90%` |
| **Data** | Thin DB helpers → [guide](https://jovijovi.github.io/pypepper/guides/helper-db/) |

## Quick start

Requires Python `3.10`–`3.14`. [uv](https://github.com/astral-sh/uv) `≥ 0.10.7` is recommended for local installs.

```shell
make build-prepare
```

SSE example (set a key; default config enables authentication):

```shell
export PYPEPPER_SSE_API_KEY=your-local-key
python example/sse/app.py
```

HTTP example:

```shell
python example/server/app.py --config ./conf/app.config.yaml
```

Scheduler end-to-end example: `python example/scheduler/app.py`.

Full walkthrough: [Getting Started](https://jovijovi.github.io/pypepper/getting-started/) · [First service tutorial](https://jovijovi.github.io/pypepper/tutorials/first-service/).

<details>
<summary><strong>Developer commands</strong></summary>

```shell
make lint     # ruff + mypy
make check    # lint + mutable class-attr guard
make test     # check + pytest (coverage ≥ 90%, branch on)
make docs     # mkdocs build --strict
make audit    # pip-audit on production requirements
make docker   # local image
make clean
```

</details>

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup, Conventional Commits, and PR expectations.
Release tags: [`docs/guides/release.md`](docs/guides/release.md).

## Security

See [`SECURITY.md`](SECURITY.md) for supported versions and private reporting.
Leaving SSE authentication off without `PYPEPPER_SSE_ALLOW_AUTH_OFF` is rejected by the library (HTTP 503).
