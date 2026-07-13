from __future__ import annotations

from types import SimpleNamespace

from opentelemetry import trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from pypepper.common.tracing import setup_for_tests, setup_from_config, shutdown


def test_setup_from_config_missing_section_disables():
    setup_from_config(SimpleNamespace())
    assert isinstance(trace.get_tracer_provider(), trace.NoOpTracerProvider)
    shutdown()


def test_setup_from_config_enabled_false():
    setup_from_config(
        SimpleNamespace(
            tracing=SimpleNamespace(
                enabled=False,
                serviceName="x",
                console=True,
                otlp=SimpleNamespace(enabled=False, endpoint="http://127.0.0.1:4318"),
            )
        )
    )
    assert isinstance(trace.get_tracer_provider(), trace.NoOpTracerProvider)
    shutdown()


def test_setup_for_tests_exports_spans():
    exporter = InMemorySpanExporter()
    setup_for_tests(exporter, service_name="console-test")
    tracer = trace.get_tracer("t")
    with tracer.start_as_current_span("console-span"):
        pass
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "console-span"
    shutdown()


def test_setup_otlp_configures_provider_without_network():
    """OTLP exporter is constructed; do not emit spans (would retry against :4318)."""
    setup_from_config(
        SimpleNamespace(
            tracing=SimpleNamespace(
                enabled=True,
                serviceName="otlp-test",
                console=False,
                otlp=SimpleNamespace(enabled=True, endpoint="http://127.0.0.1:4318"),
            ),
            serviceInfo=SimpleNamespace(serviceName="fallback"),
        )
    )
    provider = trace.get_tracer_provider()
    assert provider.__class__.__name__ == "TracerProvider"
    shutdown()


def test_setup_enabled_without_exporters_is_noop():
    setup_from_config(
        SimpleNamespace(
            tracing=SimpleNamespace(
                enabled=True,
                serviceName="noop",
                console=False,
                otlp=SimpleNamespace(enabled=False, endpoint="http://127.0.0.1:4318"),
            )
        )
    )
    assert isinstance(trace.get_tracer_provider(), trace.NoOpTracerProvider)
    shutdown()


def test_setup_service_name_fallback_and_default():
    setup_from_config(
        SimpleNamespace(
            tracing=SimpleNamespace(
                enabled=True,
                serviceName=None,
                console=True,
                otlp=SimpleNamespace(enabled=False, endpoint="http://127.0.0.1:4318"),
            ),
            serviceInfo=SimpleNamespace(serviceName="from-service-info"),
        )
    )
    assert trace.get_tracer_provider().__class__.__name__ == "TracerProvider"
    shutdown()

    setup_from_config(
        SimpleNamespace(
            tracing=SimpleNamespace(
                enabled=True,
                serviceName=None,
                console=True,
                otlp=SimpleNamespace(enabled=False, endpoint="http://127.0.0.1:4318"),
            )
        )
    )
    assert trace.get_tracer_provider().__class__.__name__ == "TracerProvider"
    shutdown()


def test_setup_tracing_cfg_none():
    setup_from_config(SimpleNamespace(tracing=None))
    assert isinstance(trace.get_tracer_provider(), trace.NoOpTracerProvider)
    shutdown()
