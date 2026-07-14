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

## Persistence stub

`Job.save()` currently logs only; there is no durable job store.

See also: [API Reference / Scheduler](../reference/scheduler.md).
