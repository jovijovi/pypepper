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


def test_http_middleware_records_query_and_server_error():
    exporter = InMemorySpanExporter()
    setup_for_tests(exporter, service_name="http-error-test")

    app = FastAPI()

    @app.get("/boom")
    def boom():
        from fastapi.responses import JSONResponse

        return JSONResponse({"ok": False}, status_code=500)

    handlers.use_middleware(app)
    client = TestClient(app)
    response = client.get("/boom?x=1", headers={"X-Request-ID": "req-err"})
    assert response.status_code == 500

    spans = [s for s in exporter.get_finished_spans() if s.name.startswith("GET ")]
    assert len(spans) == 1
    span = spans[0]
    assert span.attributes.get("url.query") == "x=1"
    assert span.attributes.get("http.status_code") == 500
    assert span.attributes.get("request_id") == "req-err"

    shutdown()


def test_http_middleware_records_unhandled_exception():
    exporter = InMemorySpanExporter()
    setup_for_tests(exporter, service_name="http-exc-test")

    app = FastAPI()

    @app.get("/raise")
    def raise_it():
        raise RuntimeError("explode")

    handlers.use_middleware(app)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/raise", headers={"X-Request-ID": "req-raise"})
    assert response.status_code == 500

    spans = [s for s in exporter.get_finished_spans() if s.name.startswith("GET ")]
    assert len(spans) == 1
    assert spans[0].status.status_code.name == "ERROR"

    shutdown()
