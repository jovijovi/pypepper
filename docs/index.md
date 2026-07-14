# PyPepper

PyPepper is a microservice toolkit for Python (`>=3.10, <=3.14`).
It provides reusable building blocks rather than a full application framework.

Published docs: <https://jovijovi.github.io/pypepper/>

## Domains

| Domain | Package | Role |
|--------|---------|------|
| Common | `pypepper.common` | Config, logging, context, cache, crypto, utilities |
| Event | `pypepper.event` | Signed domain events with JSON marshal |
| FSM | `pypepper.fsm` | Event-triggered finite state machine with rollback |
| Scheduler | `pypepper.scheduler` | Job → Channel → Worker → Workflow pipeline |
| Network | `pypepper.network` | FastAPI HTTP server and SSE subsystem |
| Helper | `pypepper.helper` | Thin MySQL / PostgreSQL / MongoDB connectors |

## Where to start

1. [Getting Started](getting-started.md) — install, test, run examples
2. [Architecture](architecture.md) — layering, extension points, singletons
3. Domain guides under **Guides** for copy-paste snippets
4. [API Reference](reference/index.md) — generated signatures and docstrings

## Examples

- `example/server/app.py` — minimal HTTP handlers
- `example/sse/app.py` — SSE with API key auth and rate limiting

```shell
export PYPEPPER_SSE_API_KEY=your-local-key
python example/sse/app.py
```
