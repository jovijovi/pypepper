# Scheduler

Workflow-based job pipeline: **Task → Workflow → Job → Channel → Worker**.

## Minimal path

```python
import asyncio

from pypepper.scheduler.channel import manager
from pypepper.scheduler.executor import CallableExecutor
from pypepper.scheduler.job import Job
from pypepper.scheduler.task import Task
from pypepper.scheduler.worker import Worker
from pypepper.scheduler.workflow import Workflow


def work(task, context):
    return {"ok": True, "task": task.name}


workflow = Workflow()
workflow.add_task(
    Task(
        channel_id="demo-channel",
        dag_id="dag-1",
        fingerprint="fp-1",
        name="step-1",
        category="demo",
        description="first step",
        tags=[],
        executor=CallableExecutor(work),
        retry_count=1,
        retry_delay=0,
        optional=False,
    )
)

job = Job(category="demo", channel_id="demo-channel")
job.workflows.append(workflow)
job.scheduled()  # dispatch into channel via Dispatcher

worker = Worker(manager.available("demo-channel"))
asyncio.run(worker.run_once())
```

## Status machine

Each `Job` owns an FSM from `build_scheduler_fsm()`:

| Event | Typical transition |
|-------|--------------------|
| `INIT` | → initializing |
| `SCHEDULE` | → scheduled |
| `RUN` | → in progress |
| `COMPLETE` | → completed |
| `FAIL` | → failed |
| `CANCEL` | → cancelled |

## Workflow retries

`Workflow.run()` executes tasks sequentially and respects:

- `retry_count` / `retry_delay`
- `optional` (failed optional tasks continue the workflow)

!!! warning "Fields not wired yet"
    These attributes exist on `Task` / `IBase` but are **not** used by `Workflow._run_task`:

    - `retry_until_completed`
    - `round_timeout`
    - `round_times`

    Prefer `retry_count` / `retry_delay` / `optional` until those semantics land.

## Persistence

`Job.save()` upserts a **metadata snapshot** (`JobRecord`) into the process-wide job store.
Workflows / executors are **not** serialized.

Default backend is **in-memory**. Switch to a database with `configure_job_store` (or YAML `scheduler.jobStore`):

| Backend | Notes |
|---------|--------|
| `memory` | Default; process-local |
| `postgres` | SQLAlchemy table `scheduler_jobs` |
| `mysql` | Same table via PyMySQL |
| `mongodb` | mongoengine collection `scheduler_jobs` |

```python
from pypepper.scheduler.job import Job
from pypepper.scheduler.store import configure_job_store, get_job_store

configure_job_store(
    "postgres",
    uri="postgresql+psycopg://postgres:example@localhost:5432/mock_pypepper",
)

job = Job(category="demo", channel_id="demo-channel")
job.scheduled()  # INIT → SCHEDULE → save()

saved = Job.get_saved(job.id)
assert saved is not None
assert saved.status == "Scheduled"

# Or query the store directly
assert get_job_store().get(job.id) is not None
```

YAML (optional):

```yaml
scheduler:
  jobStore:
    backend: postgres   # memory | postgres | mysql | mongodb
    uri: postgresql+psycopg://postgres:example@localhost:5432/mock_pypepper
```

Connections reuse [`helper.db`](helper-db.md) settings style (`uri` or discrete host/user/password/db).
`Worker` also calls `save()` after `RUN` / `COMPLETE` / `FAIL`.

### Persist-failure rules

- **Before work** (`dispatch` schedule / enqueue): roll back FSM (and remove Scheduled store row on channel-full) so `scheduled()` can retry.
- **After work** (COMPLETE/FAIL): keep the terminal FSM; retry `job.save()` only — do not re-run workflows because the snapshot write failed.
- `Job.save()` updates in-memory `status`/`updated` only after the store `put` succeeds.
- `Job.to_record()` reports FSM status (authoritative), which may lead durable `Job.status` when a terminal persist fails.

See also: [API Reference / Scheduler](../reference/scheduler.md).
