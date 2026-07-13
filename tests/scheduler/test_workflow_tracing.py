from __future__ import annotations

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from pypepper.common.tracing import setup_for_tests, shutdown
from pypepper.scheduler.executor import CallableExecutor
from pypepper.scheduler.task import Task
from pypepper.scheduler.workflow import Workflow


def test_workflow_run_creates_span():
    exporter = InMemorySpanExporter()
    setup_for_tests(exporter, service_name="workflow-test")

    def _run(task, context):
        return "ok"

    task = Task(
        channel_id="c",
        dag_id="d",
        fingerprint="f",
        name="t",
        category="c",
        description="",
        tags=[],
        executor=CallableExecutor(_run),
    )
    workflow = Workflow()
    workflow.add_task(task)
    assert workflow.run() == ["ok"]

    spans = exporter.get_finished_spans()
    names = [s.name for s in spans]
    assert "scheduler.workflow.run" in names

    shutdown()
