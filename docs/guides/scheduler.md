# Scheduler

Workflow-based job pipeline: **Task → Workflow → Job → Channel → Worker**.

## Minimal path

See the runnable example [`example/scheduler/app.py`](https://github.com/jovijovi/pypepper/blob/main/example/scheduler/app.py)
(`load_config` → `setup_from_config` → `Job.scheduled` → `Worker` → COMPLETE).

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
# Optional: create a bounded channel *before* worker/dispatch (default is unbounded).
# manager.new("demo-channel", maxsize=100)
job.scheduled()  # dispatch into channel via Dispatcher

worker = Worker(manager.available("demo-channel"))
asyncio.run(worker.run_once())
```

Create a bounded channel with `manager.new(channel_id, maxsize=N)` (or
`available(..., maxsize=N)` on first create) **before** `Worker` /
`Job.scheduled()`. If the channel already exists, a later `maxsize` is ignored
(same instance). Full send returns `False` from `Channel.send`;
`Job.scheduled()` raises `ChannelFullError` when enqueue is rejected.

## Status machine

Each `Job` owns an FSM from `build_scheduler_fsm()`:

| Event | Typical transition |
|-------|--------------------|
| `INIT` | → initializing |
| `SCHEDULE` | → scheduled |
| `RUN` | → in progress |
| `COMPLETE` | → completed |
| `FAIL` | → failed |
| `CANCEL` | scheduled or in progress → cancelled |

`Job.cancel()` applies `CANCEL` and persists. Cancellation is cooperative: the Worker
skips work if the job is already cancelled, and stops before `COMPLETE` at workflow
boundaries. It does **not** interrupt a sync workflow mid-`to_thread`. `Channel.stop`
only stops the consumer loop; it is not job cancel.

## Workflow retries and rounds

`Workflow.run()` executes tasks sequentially. Per task:

| Field | Behavior |
|-------|----------|
| `retry_count` / `retry_delay` | When until is false, or until + `retry_count > 0`: up to `retry_count + 1` attempts per round, with `retry_delay` seconds between failures. When until + `retry_count == 0`, the attempt budget is `retry_until_max` instead (see below). Both must be `>= 0` |
| `retry_until_completed` | When `True` and `retry_count == 0`, retry until success up to `retry_until_max` (default 1000) **per round**. When `True` and `retry_count > 0`, `retry_count` is the cap (`count + 1` attempts); `retry_until_max` is ignored |
| `retry_until_max` | Per-round attempt cap for until-retries (`>= 1`); only when until + `retry_count == 0`. Not a global cap across `round_times` |
| `round_times` | Outer rounds (default 1); each round gets a fresh inner retry budget. Success returns early; later rounds run only after a full failed inner budget. No delay between rounds |
| `round_timeout` | Soft timeout in **seconds** for a single `execute` call (`0` = none). Timeout counts as a failed attempt. If work is still **queued**, the Future is cancelled when possible (`timed out before start`). If `execute` already **started**, the pool thread is not cancelled (`execute still running`) and may overlap the next attempt on a **shared** soft-timeout pool (≤32 concurrent soft-timeout executes in-process, including orphans). Further work **queues** (`submit` does not block). Prefer idempotent executors. Caps threads, not queue memory |
| `optional` | Failed optional tasks continue the workflow |

Non-optional task failure after all rounds/attempts aborts the workflow.

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

YAML (optional). `config.load_config()` does **not** apply this automatically — call
`setup_from_config` after load (a durable `backend` without setup/configure/set makes
`Job.save` / `Job.get_saved` raise `ValueError`; `reset_job_store` re-arms that guard
from the current YAML). Explicitly installing an in-memory store via
`configure_job_store("memory")` / `set_job_store(...)` clears the deferred guard and
emits a one-shot warning that persistence will not use the YAML durable backend
(`reset_job_store` clears that one-shot for the next install cycle):

```python
from pypepper.common.config import config
from pypepper.scheduler.store import setup_from_config

config.load_config("./conf/app.config.yaml")
setup_from_config(config.get_yml_config())
```

```yaml
scheduler:
  jobStore:
    backend: postgres   # memory | postgres | mysql | mongodb
    uri: postgresql+psycopg://postgres:example@localhost:5432/mock_pypepper
```

Connections reuse [`helper.db`](helper-db.md) settings style (`uri` or discrete host/user/password/db).
`Worker` also calls `save()` after `RUN` / `COMPLETE` / `FAIL` (and skips terminal
`COMPLETE` when the job is already `Cancelled`). `Job.cancel()` persists `Cancelled`.

`Job.scheduled()` / `Processor.run` must be called from a **sync** context. They raise
`RuntimeError` if an event loop is already running. From async code: apply `INIT` then
`SCHEDULE`, call `job.save()`, then `await Channel.send(job)` and consume with `Worker`.

### Persist-failure rules

- **Schedule** (`INIT`/`SCHEDULE` + `save` in `dispatch`): roll back FSM and `Job.status` so `scheduled()` can retry (no store delete needed if `save` never succeeded).
- **Enqueue** (channel/processor setup or send rejected): roll back FSM/`Job.status` and best-effort delete the Scheduled store row. If delete fails, a Scheduled row may remain (ghost). After the job is successfully sent to the channel, do **not** roll back — a raised error then is a committed enqueue plus secondary failure (the job may still run); do not treat it as “nothing queued.”
- **Start (`RUN`)**: if Running snapshot fails, do not run workflows; prefer persist `Failed`. If that also fails and the job is already `Cancelled`, keep Cancelled and retry `job.save()` only — do **not** restore pre-RUN over a winning cancel. Otherwise restore pre-RUN.
- **After work** (COMPLETE/FAIL via Worker): keep the terminal FSM; retry `job.save()` only — do not re-run workflows because the snapshot write failed.
- **Cancel** (`Job.cancel()`): apply `CANCEL` then `save()`; on persist failure keep Cancelled in the FSM and retry `job.save()` only. The Worker does not apply `CANCEL` — it skips or exits when the job is already cancelled (and retries Cancelled persist if the store lags).
- `Job.save()` updates in-memory `status`/`updated` only after the store `put` succeeds.
- `Job.to_record()` reports FSM status (authoritative), which may lead last durable store status and in-memory `Job.status` when a terminal persist fails.
- `IJobStore.put` upserts by `id` and must not overwrite an existing row's `created`.
- Invalid FSM transitions raise; do not persist or run work after a failed transition.

See also: [API Reference / Scheduler](../reference/scheduler.md).
