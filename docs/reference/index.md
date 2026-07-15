# API Reference

Machine-generated reference from the `pypepper` package (signatures, types, and existing docstrings).

Stable curated imports live on domain packages (for example `from pypepper.scheduler import Job`).
For `common`, use submodule paths (`from pypepper.common.config import config`) so package-level
names do not shadow `pypepper.common.config` / `pypepper.common.log`. Deep module paths elsewhere
remain usable but are not a long-term stability guarantee.

| Section | Package focus |
|---------|---------------|
| [Common](common.md) | Config, log, context, cache, crypto, tracing |
| [Event and FSM](event-fsm.md) | Signed events and finite state machines |
| [Scheduler](scheduler.md) | Job pipeline: task, workflow, channel, worker |
| [Network and SSE](network.md) | FastAPI HTTP server and SSE |
| [DB Helper](helper.md) | MySQL, PostgreSQL, MongoDB connectors |
| [Loader](loader.md) | Named module init hooks |

For narrative how-tos, use the [Guides](../guides/common.md). For layering and singletons, see [Architecture](../architecture.md).
