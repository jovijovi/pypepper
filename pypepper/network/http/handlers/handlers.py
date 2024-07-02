from fastapi import FastAPI

from pypepper.network.http.handlers.base import health, metrics, ping
from pypepper.network.http.interfaces import ITaskHandler


class BaseHandlers(ITaskHandler):
    def register_handlers(self, app: FastAPI):
        self._register_health_check(app)
        self._register_metrics_check(app)

    def use_middleware(self, app: FastAPI):
        self._use_default_middleware(app)

    @staticmethod
    def _register_health_check(app: FastAPI):
        app.get('/health')(health)
        app.get('/ping')(ping)

    @staticmethod
    def _register_metrics_check(app: FastAPI):
        app.get('/metrics')(metrics)

    # TODO:
    def _use_default_middleware(self, app: FastAPI):
        pass


base_handlers = BaseHandlers()


def register_handlers(app: FastAPI, private_handlers: ITaskHandler):
    base_handlers.register_handlers(app)
    if private_handlers:
        private_handlers.register_handlers(app)
