from flask import Flask

from pypepper.common import system
from pypepper.common.config import config
from pypepper.common.log import log
from pypepper.logo import logo
from pypepper.network.http import server
from pypepper.network.http.interfaces import ITaskHandler


def biz1():
    log.request_id().debug("biz1")
    return "biz1"


def biz2():
    log.request_id().info("biz2")
    return "biz2"


def register_biz_api(app: Flask):
    app.add_url_rule('/api/v1/biz1', view_func=biz1, methods=['GET'])
    app.add_url_rule('/api/v1/biz2', view_func=biz2, methods=['POST'])


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
