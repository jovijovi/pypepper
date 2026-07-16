"""
Scheduler end-to-end example: config → job store → Job.scheduled → Worker → COMPLETE.

Usage (from repo root):

    python example/scheduler/app.py
"""

from __future__ import annotations

import asyncio

from pypepper.common.config import config
from pypepper.common.log import log
from pypepper.logo import logo
from pypepper.scheduler.channel import manager
from pypepper.scheduler.executor import CallableExecutor
from pypepper.scheduler.job import Job
from pypepper.scheduler.status import Status
from pypepper.scheduler.store import setup_from_config
from pypepper.scheduler.task import Task
from pypepper.scheduler.worker import Worker
from pypepper.scheduler.workflow import Workflow

CHANNEL_ID = "example-scheduler"


def work(task, context):
    log.info(f"running task={task.name}")
    return {"ok": True, "task": task.name}


def build_job() -> Job:
    workflow = Workflow()
    workflow.add_task(
        Task(
            channel_id=CHANNEL_ID,
            dag_id="dag-1",
            fingerprint="fp-1",
            name="step-1",
            category="demo",
            description="scheduler e2e step",
            tags=["example"],
            executor=CallableExecutor(work),
            retry_count=0,
            retry_delay=0,
            optional=False,
        )
    )
    job = Job(category="demo", channel_id=CHANNEL_ID)
    job.workflows.append(workflow)
    return job


async def run_worker(job: Job) -> None:
    worker = Worker(manager.available(CHANNEL_ID))
    processed = await worker.run_once()
    assert processed is job
    assert job._fsm.current().value == Status.COMPLETED
    saved = Job.get_saved(job.id)
    assert saved is not None
    assert saved.status == Status.COMPLETED.value
    log.info(f"job completed: id={job.id} status={saved.status}")


def main() -> None:
    log.logo(logo)
    config.load_config("./conf/app.config.yaml")
    setup_from_config(config.get_yml_config())

    # Job.scheduled() must run in a sync context (no running event loop).
    job = build_job()
    job.scheduled()
    log.info(f"job scheduled: id={job.id} status={job.status}")

    asyncio.run(run_worker(job))


if __name__ == "__main__":
    main()
