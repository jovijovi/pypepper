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
(same instance). `Channel.send` returns `"ok"`, `"full"`, or `"stopped"`
(decided under the same lock as `request_stop`). `Job.scheduled()` raises
`ChannelFullError` when the queue is full, or `ChannelStoppedError` when the
channel is stopped. Both are siblings under `ChannelEnqueueError` (stopped is
**not** a subclass of full). Catch `ChannelStoppedError` / `ChannelEnqueueError`
explicitly — do not treat stop as capacity backpressure. Both are pre-enqueue
failures (safe to roll back). Prefer `Job.scheduled()` from sync code so
failures raise typed errors. Do not classify a failed send by reading
`channel.stop` afterwards.

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

`Job.cancel()` applies `CANCEL`, sets a `threading.Event` in `Job.context`
(`CANCEL_EVENT_KEY`), and persists. Executors may poll that event; `CallableExecutor`
does not wrap user functions. Cancellation is cooperative: the Worker
skips work if the job is already cancelled, and stops before `COMPLETE` at workflow
boundaries. It does **not** interrupt a sync workflow mid-`to_thread`. Prefer
`Channel.request_stop()` to stop the consumer loop (sets read-only `stop` and wakes a
blocked `receive()` via an event, without occupying queue slots). `send` and
`request_stop` are serialized on an instance lock: a successful enqueue and a
stop-reject are mutually exclusive. While stopped, `Channel.send` returns `"stopped"` and
`Job.scheduled()` raises `ChannelStoppedError`. Worker **drains** leftovers after
stop: `run_once` still calls `receive()` (stop + empty → `None`; stop + queued →
process the job). `run_forever` exits when `run_once` returns `None` (stopped and
empty), not on an idle empty queue alone. Stop is **not** job cancel — queued jobs
still run; use `Job.cancel()` for cancel semantics.
`Channel.stop` / `request_stop` are not job cancel.

`Worker.run_forever` logs job errors and continues (behavior change vs raise-and-exit).
Exit when `run_once` returns `None` (channel stopped **and** empty), not on an idle empty
queue alone. Continue-on-error does not by itself redeliver: after a RUN-start persist
failure that restores pre-RUN, the Worker re-enqueues when possible and raises
`JobRequeuedError` so `run_forever` **re-raises** (job stays queued; avoids busy-spin;
supervisors see a non-success exit). If re-enqueue fails because the channel is full,
`JobRedeliveryError` (`.reason` of `full`) stops the loop immediately. If it fails
because the channel is stopped, leftovers are still drained, then
`JobRedeliveryError` (`.reason` of `stopped`) is re-raised. If re-enqueue is
impossible, the unrestored job is persisted as Failed and attached as
`.job`. `JobRequeuedError` is **re-raised immediately** (not continued) so a
persist-failing job cannot busy-spin `run_forever`.

## Workflow retries and rounds

`Workflow.run()` executes tasks sequentially. Per task:

| Field | Behavior |
|-------|----------|
| `retry_count` / `retry_delay` | When until is false, or until + `retry_count > 0`: up to `retry_count + 1` attempts per round, with `retry_delay` seconds between failures. When until + `retry_count == 0`, the attempt budget is `retry_until_max` instead (see below). Both must be `>= 0` |
| `retry_until_completed` | When `True` and `retry_count == 0`, retry until success up to `retry_until_max` (default 1000) **per round**. When `True` and `retry_count > 0`, `retry_count` is the cap (`count + 1` attempts); `retry_until_max` is ignored |
| `retry_until_max` | Per-round attempt cap for until-retries (`>= 1`); only when until + `retry_count == 0`. Not a global cap across `round_times` |
| `round_times` | Outer rounds (default 1); each round gets a fresh inner retry budget. Success returns early; later rounds run only after a full failed inner budget. No delay between rounds |
| `round_timeout` | Timeout in **seconds** for a single `execute` call (`0` = none). Timeout counts as a failed attempt. If work is still **queued**, the Future is cancelled when possible (`timed out before start`). If `execute` already **started**, the pool thread is **joined** before the next retry or `Workflow.run()` return. `round_timeout_join` bounds that wait (`0` = forever; a hung execute then blocks this workflow / Worker). A still-running Future blocks a later attempt for the same task (no overlapping submit). A shared pool caps concurrent timeout executes (≤32); further work **queues**. Bounded join can leave at most 32 orphan pool threads. Prefer idempotent executors |
| `round_timeout_join` | Extra seconds to join a started execute after `round_timeout` (`0` = wait forever) |
| `optional` | Failed optional tasks continue the workflow |

Non-optional task failure after all rounds/attempts aborts the workflow.

## Persistence

`Job.save()` upserts a **metadata snapshot** (`JobRecord`) into the process-wide job store.
Workflows / executors are **not** serialized unless every task has `executor_id`; then
`to_record()` may include a JSON `payload`. Rebuild a runnable job with
`executor_registry.register(...)` and `Job.from_record(record)` (missing ids raise
`ValueError`). `put` returns `True`/`False`; a `False` skip does not rewind
`Job.status`. Successful writes increment store `version` (OCC).

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
job.scheduled()  # INIT → SCHEDULE → send → save()

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
`SCHEDULE`, `await Channel.send(job)` (must be `"ok"`; `"stopped"` / `"full"` are
rejections), then `job.save()`, and consume with `Worker`. Prefer
`Job.scheduled()` from sync code so failures raise `ChannelStoppedError` /
`ChannelFullError`. If the store has no Scheduled row when the Worker dequeues the
job, it heals that snapshot before `RUN`.

### Persist-failure rules

- **Schedule** (`INIT`/`SCHEDULE` in `dispatch`): roll back FSM and `Job.status` so `scheduled()` can retry (no store write yet).
- **Enqueue** (channel/processor setup or send rejected): roll back FSM/`Job.status` with **no store write**. After a successful send, persist Scheduled. If that `save()` fails, do **not** roll back — the job is on the channel (store may lack a Scheduled row until Worker heal / RUN `save`); do not treat it as “nothing queued.”
- **Start (`RUN`)**: if the store has no row, persist Scheduled first. If Running snapshot fails or `put` returns `False`, do not run workflows. Follow durable Cancelled/InProgress/terminals. Otherwise prefer persist `Failed`. If that also fails and the job is already `Cancelled`, keep Cancelled and retry `job.save()` only — do **not** restore pre-RUN over a winning cancel. Otherwise restore pre-RUN and **re-enqueue** when possible, then raise `JobRequeuedError` so `run_forever` **re-raises** (job stays queued; no busy-spin). If re-enqueue fails, persist Failed, set `.job`, and raise `JobRedeliveryError` (`full` stops immediately; `stopped` drains leftovers first).
- **After work** (COMPLETE/FAIL via Worker): keep the terminal FSM; retry `job.save()` only — do not re-run workflows because the snapshot write failed.
- **Cancel** (`Job.cancel()`): set the context cancel event, apply `CANCEL` then `save()`; on persist failure keep Cancelled in the FSM and retry `job.save()` only. The Worker does not apply `CANCEL` — it skips or exits when the job is already cancelled (and retries Cancelled persist if the store lags).
- `Job.save()` updates in-memory `updated` / `version` only after `put` returns `True`. `apply_event` keeps `Job.status` aligned with the FSM; skip does not rewind it.
- `Job.to_record()` reports FSM status (authoritative), which may lead last durable store status when a persist fails or is skipped.
- `IJobStore.put` upserts by `id` and must not overwrite an existing row's `created`. It must not replace a durable status with an earlier lifecycle (Scheduled cannot overwrite InProgress/terminal). Distinct terminals (Failed/Completed/Cancelled) do not overwrite each other. Updates need a matching `version` (then the store increments it). `Job.save()` does not rewind in-memory `status`/`updated` when that write is skipped (`put` returns `False`).
- Invalid FSM transitions raise; do not persist or run work after a failed transition.

See also: [API Reference / Scheduler](../reference/scheduler.md).
