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

PyPepper packages the pieces you wire into services: **HTTP / SSE**, **FSM**, a **workflow scheduler**, signed **events**, thin **DB helpers**, and optional **OpenTelemetry** tracing — for Python `3.10`–`3.14`.

- Project: [https://github.com/jovijovi/pypepper](https://github.com/jovijovi/pypepper)
- Docs: [https://jovijovi.github.io/pypepper/](https://jovijovi.github.io/pypepper/)

## Documentation

[Getting Started](https://jovijovi.github.io/pypepper/getting-started/) · [Tutorial](https://jovijovi.github.io/pypepper/tutorials/first-service/) · [Architecture](https://jovijovi.github.io/pypepper/architecture/) · [Guides](https://jovijovi.github.io/pypepper/guides/common/) · [API Reference](https://jovijovi.github.io/pypepper/reference/)

Source under [`docs/`](docs/index.md). Local preview: `make docs-serve`.

## Security

See [`SECURITY.md`](SECURITY.md) for supported versions and how to report vulnerabilities privately.

## Domains

| | Package | Role |
|:--|:--|:--|
| **Common** | `pypepper.common` | Config, logging, context, cache, crypto, utilities |
| **Event** | `pypepper.event` | Signed domain events with JSON marshal |
| **FSM** | `pypepper.fsm` | Event-triggered state machine with rollback |
| **Scheduler** | `pypepper.scheduler` | `Job → Channel → Worker → Workflow` |
| **Network** | `pypepper.network` | FastAPI HTTP server and SSE subsystem |
| **Helper** | `pypepper.helper` | MySQL / PostgreSQL / MongoDB connectors |

## Highlights

| | |
|:--|:--|
| **Network** | FastAPI HTTP + SSE with API-key auth and rate limits → [guide](https://jovijovi.github.io/pypepper/guides/network-sse/) |
| **FSM & events** | Rollback on handler failure; signed payloads → [guide](https://jovijovi.github.io/pypepper/guides/event-fsm/) |
| **Scheduler** | Workflow job pipeline with retries → [guide](https://jovijovi.github.io/pypepper/guides/scheduler/) |
| **Tracing** | Opt-in OpenTelemetry (console / local Jaeger) → [guide](https://jovijovi.github.io/pypepper/guides/tracing/) |
| **Quality** | PEP 561 `py.typed` · ruff + mypy CI · coverage `≥ 90%` |
| **Data** | Thin DB helpers → [guide](https://jovijovi.github.io/pypepper/guides/helper-db/) |

## Quick start

Requires Python `3.10`–`3.14` and [uv](https://github.com/astral-sh/uv) `≥ 0.10.7` (recommended).

```shell
make build-prepare
```

```shell
export PYPEPPER_SSE_API_KEY=your-local-key
python example/sse/app.py
```

HTTP example:

```shell
python example/server/app.py --config ./conf/app.config.yaml
```

Full walkthrough: [Getting Started](https://jovijovi.github.io/pypepper/getting-started/).

<details>
<summary><strong>Developer commands</strong></summary>

```shell
make lint     # ruff + mypy
make test     # check + pytest (coverage ≥ 90%)
make docs     # mkdocs build --strict
make docker   # local image
make clean
```

</details>
