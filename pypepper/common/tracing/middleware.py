"""Starlette/FastAPI middleware that creates SERVER spans."""

from __future__ import annotations

from opentelemetry.trace import SpanKind, Status, StatusCode
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from pypepper.common.tracing.setup import get_tracer


class TracingMiddleware(BaseHTTPMiddleware):
    """Create a SERVER span per HTTP request; attach request_id when present."""

    def __init__(self, app: ASGIApp, tracer_name: str = "pypepper.network.http"):
        super().__init__(app)
        self._tracer_name = tracer_name

    async def dispatch(self, request: Request, call_next) -> Response:
        tracer = get_tracer(self._tracer_name)
        span_name = f"{request.method} {request.url.path}"
        with tracer.start_as_current_span(span_name, kind=SpanKind.SERVER) as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.scheme", request.url.scheme)
            span.set_attribute("url.path", request.url.path)
            if request.url.query:
                span.set_attribute("url.query", request.url.query)

            try:
                response = await call_next(request)
            except Exception as exc:
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.record_exception(exc)
                raise

            req_id = getattr(request.state, "request_id", None)
            if req_id is not None:
                span.set_attribute("request_id", str(req_id))

            span.set_attribute("http.status_code", response.status_code)
            if response.status_code >= 500:
                span.set_status(Status(StatusCode.ERROR))
            return response
