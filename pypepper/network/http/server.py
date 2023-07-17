from flask import Flask

from pypepper.common.config import config
from pypepper.network.http.handlers import handlers
from pypepper.network.http.interfaces import ITaskHandler

app = Flask(__name__)


def run_without_tls(port: int, handlers_: ITaskHandler):
    handlers.register_handlers(app, handlers_)
    app.run(host='0.0.0.0', port=port)


# TODO: Run with TLS
def run_with_tls(port: int, handlers_: ITaskHandler):
    pass


def run(handlers_: ITaskHandler = None):
    network_conf = config.get_yml_config().network
    if network_conf.httpServer.enable:
        run_without_tls(network_conf.httpServer.port, handlers_)
    elif network_conf.httpsServer.enable:
        run_with_tls(network_conf.httpsServer.port, handlers_)
