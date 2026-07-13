from __future__ import annotations

import atexit
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.util._once import Once

_provider: TracerProvider | None = None
_atexit_registered = False


def get_tracer(name: str = "pypepper") -> trace.Tracer:
    """Return a tracer from the global provider (no-op when tracing is disabled)."""
    return trace.get_tracer(name)


def _allow_tracer_provider_override() -> None:
    """Reset the global once-flag so tests / reload can replace the provider."""
    trace._TRACER_PROVIDER_SET_ONCE = Once()
    trace._TRACER_PROVIDER = None


def shutdown() -> None:
    """Flush and shut down the configured TracerProvider, if any."""
    global _provider
    if _provider is not None:
        _provider.force_flush()
        _provider.shutdown()
        _provider = None
    _allow_tracer_provider_override()
    trace.set_tracer_provider(trace.NoOpTracerProvider())


def setup_from_config(yml_config: Any | None = None) -> None:
    """
    Configure OpenTelemetry from YAML config.

    Expected shape (all optional; missing section disables tracing)::

        tracing:
          enabled: false
          serviceName: pypepper
          console: false
          otlp:
            enabled: false
            endpoint: http://127.0.0.1:4318
    """
    global _provider, _atexit_registered

    shutdown()

    if yml_config is None or not hasattr(yml_config, "tracing"):
        return

    tracing_cfg = yml_config.tracing
    if tracing_cfg is None:
        return

    enabled = bool(getattr(tracing_cfg, "enabled", False))
    if not enabled:
        return

    service_name = getattr(tracing_cfg, "serviceName", None)
    if not service_name and hasattr(yml_config, "serviceInfo"):
        service_name = getattr(yml_config.serviceInfo, "serviceName", None)
    if not service_name:
        service_name = "pypepper"

    console = bool(getattr(tracing_cfg, "console", False))
    otlp_cfg = getattr(tracing_cfg, "otlp", None)
    otlp_enabled = bool(getattr(otlp_cfg, "enabled", False)) if otlp_cfg is not None else False
    otlp_endpoint = (getattr(otlp_cfg, "endpoint", None) if otlp_cfg is not None else None) or "http://127.0.0.1:4318"

    if not console and not otlp_enabled:
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if console:
        # Simple processor so spans appear promptly in the terminal during local demos.
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    if otlp_enabled:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        endpoint = str(otlp_endpoint).rstrip("/")
        if not endpoint.endswith("/v1/traces"):
            endpoint = f"{endpoint}/v1/traces"
        # Simple processor so local Jaeger UI sees spans without waiting for a batch flush.
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(SimpleSpanProcessor(exporter))

    _allow_tracer_provider_override()
    trace.set_tracer_provider(provider)
    _provider = provider

    if not _atexit_registered:
        atexit.register(shutdown)
        _atexit_registered = True


def setup_for_tests(exporter: Any, service_name: str = "pypepper-test") -> TracerProvider:
    """
    Install a TracerProvider that exports to the given span exporter (tests only).

    Uses SimpleSpanProcessor so spans are available immediately after the request.
    """
    global _provider
    shutdown()
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    _allow_tracer_provider_override()
    trace.set_tracer_provider(provider)
    _provider = provider
    return provider
