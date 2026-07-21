"""Deferred durable jobStore fail-fast on dispatch / Worker paths."""

from __future__ import annotations

import pytest

from pypepper.common.config import config
from pypepper.scheduler.channel import manager
from pypepper.scheduler.executor import CallableExecutor
from pypepper.scheduler.job import Job
from pypepper.scheduler.status import Status
from pypepper.scheduler.store import (
    configure_job_store,
    reset_job_store,
    reset_job_store_mismatch_warning,
)
from pypepper.scheduler.task import Task
from pypepper.scheduler.worker import Worker
from pypepper.scheduler.workflow import Workflow


def _write_durable_cfg(tmp_path, name: str = "durable-jobstore.yaml"):
    cfg = tmp_path / name
    cfg.write_text(
        "scheduler:\n"
        "  jobStore:\n"
        "    backend: postgres\n"
        "    uri: postgresql+psycopg://postgres:example@localhost:5432/mock_pypepper\n"
    )
    return cfg


def _restore_memory_config() -> None:
    """Avoid leaving durable YAML in the process-wide config for later tests."""
    config.load_config("./conf/app.config.yaml")
    config.mark_scheduler_job_store_applied()


def test_scheduled_raises_when_durable_job_store_deferred(tmp_path):
    channel_id = "deferred-sched-ch"
    chan = manager.available(channel_id)
    cfg = _write_durable_cfg(tmp_path)
    try:
        config.load_config(str(cfg))
        job = Job(category="deferred", channel_id=channel_id)

        with pytest.raises(ValueError, match="setup_from_config"):
            job.scheduled()

        assert job._fsm.current().value == Status.UNKNOWN
        assert job.status == Status.UNKNOWN.value
        assert chan.length() == 0

        config.mark_scheduler_job_store_applied()
        assert Job.get_saved(job.id) is None
    finally:
        _restore_memory_config()


@pytest.mark.asyncio
async def test_worker_run_save_deferred_restores_pre_run(tmp_path):
    """
    After a successful enqueue, re-arm deferred via reset_job_store; Worker RUN
    save must fail-fast and restore pre-RUN (Scheduled).

    Uses INIT→SCHEDULE→save→send (async-safe) instead of Job.scheduled(), which
    cannot run under a live event loop.
    """
    from pypepper.scheduler import events

    channel_id = "deferred-worker-ch"
    executed: list[str] = []

    def work(task, context):
        executed.append(task.name)
        return "ok"

    workflow = Workflow()
    workflow.add_task(
        Task(
            channel_id=channel_id,
            dag_id="dag",
            fingerprint="fp",
            name="step1",
            category="c",
            description="",
            tags=[],
            executor=CallableExecutor(work),
            retry_count=0,
        )
    )

    cfg = _write_durable_cfg(tmp_path, name="durable-worker.yaml")
    try:
        config.load_config(str(cfg))
        reset_job_store_mismatch_warning()
        configure_job_store("memory")

        job = Job(category="deferred", channel_id=channel_id)
        job.workflows = [workflow]
        assert job._fsm.on(events.INIT).error is None
        assert job._fsm.on(events.SCHEDULE).error is None
        job.save()
        chan = manager.available(channel_id)
        assert await chan.send(job)
        assert chan.length() == 1
        assert job._fsm.current().value == Status.SCHEDULED

        reset_job_store()
        assert config._deferred_durable_job_store_backend == "postgres"

        with pytest.raises(ValueError, match="setup_from_config"):
            await Worker(chan).run_once()

        assert executed == []
        assert job._fsm.current().value == Status.SCHEDULED
        assert job.status == Status.SCHEDULED.value

        config.mark_scheduler_job_store_applied()
        assert Job.get_saved(job.id) is None
    finally:
        reset_job_store_mismatch_warning()
        _restore_memory_config()
