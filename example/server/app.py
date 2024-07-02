from fastapi import FastAPI

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


def register_biz_api(app: FastAPI):
    app.get('/api/v1/biz1')(biz1)
    app.post('/api/v1/biz2')(biz2)


class AppHandlers(ITaskHandler):
    def register_handlers(self, app: FastAPI):
        register_biz_api(app)

    def use_middleware(self, app: FastAPI):
        pass


app_handlers = AppHandlers()


def main():
    log.logo(logo)
    system.handle_signals()
    config.load_config()

    server.run(app_handlers)


if __name__ == '__main__':
    main()
