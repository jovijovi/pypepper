# First service: config → job store → Job → Worker → COMPLETE

This tutorial is a **single narrative path** with expected outcomes and common
pitfalls. For install commands and the full example list, see
[Getting Started](../getting-started.md).

## Goal

From a clean checkout, run the scheduler example so a job reaches **Completed**
in the in-memory job store.

## Prerequisites

- Python `3.10`–`3.14` and repo dependencies (`make build-prepare` or
  `uv pip install -r requirements-dev.txt` then `requirements.txt`)
- Work from the **repository root** (config and example paths are relative)

## Step 1 — Load config and wire the job store

`config.load_config()` applies log/tracing settings. It does **not** configure a
durable `scheduler.jobStore`. Always call `setup_from_config` after load when
YAML declares a store (even `memory`).

```python
from pypepper.common.config import config
from pypepper.scheduler.store import setup_from_config

config.load_config("./conf/app.config.yaml")
setup_from_config(config.get_yml_config())
```

!!! failure "Forgot `setup_from_config`?"
    A non-`memory` `scheduler.jobStore.backend` in YAML makes `Job.save` /
    `Job.get_saved` raise `ValueError` until you call `setup_from_config`
    (or `configure_job_store` / `set_job_store`). Declaring `backend: memory`
    does not arm that guard.

## Step 2 — Run the scheduler example

```shell
python example/scheduler/app.py
```

What it does:

1. Builds a one-task workflow with `CallableExecutor`
2. Calls `Job.scheduled()` in a **sync** context (required — no running event loop)
3. Runs `Worker.run_once()` until the job finishes

### Expected outcome

Logs should include a line that the job completed, for example:

```text
job completed: id=... status=Completed
```

The process exits `0`. If an assertion fails inside the example, you will see a
traceback instead.

!!! failure "Called `scheduled()` from async code?"
    `Job.scheduled()` / `Processor.run` raise `RuntimeError` when an event loop is
    already running. Keep scheduling in sync code (as the example does), then
    `asyncio.run` only the worker.

## Step 3 (optional) — SSE echo stream

In another terminal:

```shell
export PYPEPPER_SSE_API_KEY=your-local-key
python example/sse/app.py
```

Connect:

```shell
curl -N -H "X-API-Key: $PYPEPPER_SSE_API_KEY" http://localhost:55550/sse/echo
```

You should see SSE event frames. Keep
`sse.authentication.enabled: true` outside local experiments
(see [SSE security notes](../guides/network-sse.md#security-notes)).

## Next

- [Scheduler guide](../guides/scheduler.md) — cancel, persistence, job stores
- [Architecture](../architecture.md) — domain boundaries
- [API Reference](../reference/index.md)
