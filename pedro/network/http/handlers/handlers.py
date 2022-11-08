from flask import Flask

from pedro.network.http.handlers.base import health, metrics


def register_handlers(app: Flask):
    app.add_url_rule("/health", view_func=health)
    app.add_url_rule("/metrics", view_func=metrics)
