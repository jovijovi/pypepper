from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from pypepper.common.log import log
from pypepper.common.utils import uuid
from pypepper.network.http.handlers.base import health, metrics, ping
from pypepper.network.http.interfaces import ITaskHandler


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Inject X-Request-ID and emit a basic access log line."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or uuid.new_uuid()
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        log.request_id(req_id).info(f"{request.method} {request.url.path} -> {response.status_code}")
        return response


class BaseHandlers(ITaskHandler):
    def register_handlers(self, app: FastAPI):
        self._register_health_check(app)
        self._register_metrics_check(app)

    def use_middleware(self, app: FastAPI):
        self._use_default_middleware(app)

    @staticmethod
    def _register_health_check(app: FastAPI):
        app.get("/health")(health)
        app.get("/ping")(ping)

    @staticmethod
    def _register_metrics_check(app: FastAPI):
        app.get("/metrics")(metrics)

    def _use_default_middleware(self, app: FastAPI):
        app.add_middleware(RequestIdMiddleware)


base_handlers = BaseHandlers()


def register_handlers(app: FastAPI, private_handlers: ITaskHandler | None = None):
    base_handlers.register_handlers(app)
    if private_handlers:
        private_handlers.register_handlers(app)


def use_middleware(app: FastAPI, private_handlers: ITaskHandler | None = None):
    base_handlers.use_middleware(app)
    if private_handlers:
        private_handlers.use_middleware(app)
