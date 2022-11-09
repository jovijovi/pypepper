from flask import Flask

from pedro.common import system
from pedro.common.config import config
from pedro.common.log import log
from pedro.logo import logo
from pedro.network.http import server
from pedro.network.http.interfaces import ITaskHandler


def biz1():
    log.request_id().debug("biz1")
    return "biz1"


def biz2():
    log.request_id().info("biz2")
    return "biz2"


def register_biz_api(app: Flask):
    app.add_url_rule('/api/v1/biz1', view_func=biz1)
    app.add_url_rule('/api/v1/biz2', view_func=biz2)


class AppHandlers(ITaskHandler):
    def register_handlers(self, app: Flask):
        register_biz_api(app)

    def use_middleware(self, app: Flask):
        pass


app_handlers = AppHandlers()


def main():
    log.logo(logo)
    system.handle_signals()
    config.load_config()

    server.run(app_handlers)


if __name__ == '__main__':
    main()
