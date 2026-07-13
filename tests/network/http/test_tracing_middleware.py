from __future__ import annotations

from fastapi import FastAPI
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from starlette.testclient import TestClient

from pypepper.common.tracing import setup_for_tests, shutdown
from pypepper.network.http.handlers import handlers


def test_http_middleware_creates_server_span_with_request_id():
    exporter = InMemorySpanExporter()
    setup_for_tests(exporter, service_name="http-test")

    app = FastAPI()
    handlers.register_handlers(app)
    handlers.use_middleware(app)

    client = TestClient(app)
    response = client.get("/health", headers={"X-Request-ID": "req-trace-1"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "req-trace-1"

    spans = exporter.get_finished_spans()
    assert len(spans) >= 1
    http_spans = [s for s in spans if s.name.startswith("GET ")]
    assert len(http_spans) == 1
    span = http_spans[0]
    assert span.attributes.get("http.method") == "GET"
    assert span.attributes.get("url.path") == "/health"
    assert span.attributes.get("request_id") == "req-trace-1"
    assert span.attributes.get("http.status_code") == 200

    shutdown()
