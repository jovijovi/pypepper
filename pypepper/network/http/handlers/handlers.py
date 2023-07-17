from flask import Flask

from pypepper.network.http.handlers.base import health, metrics, ping
from pypepper.network.http.interfaces import ITaskHandler


class BaseHandlers(ITaskHandler):
    def register_handlers(self, app: Flask):
        self._register_health_check(app)
        self._register_metrics_check(app)

    def use_middleware(self, app: Flask):
        self._use_default_middleware(app)

    @staticmethod
    def _register_health_check(app: Flask):
        app.add_url_rule('/health', view_func=health, methods=['GET'])
        app.add_url_rule('/ping', view_func=ping, methods=['GET'])

    @staticmethod
    def _register_metrics_check(app: Flask):
        app.add_url_rule('/metrics', view_func=metrics, methods=['GET'])

    # TODO:
    def _use_default_middleware(self, app: Flask):
        pass


base_handlers = BaseHandlers()


def register_handlers(app: Flask, private_handlers: ITaskHandler):
    base_handlers.register_handlers(app)
    if private_handlers:
        private_handlers.register_handlers(app)
