from flask import Flask

from pedro.common.config import config
from pedro.network.http.handlers import handlers

app = Flask(__name__)


def run_without_tls(port: int):
    handlers.register_handlers(app)
    app.run(host='0.0.0.0', port=port)


# TODO: Run with TLS
def run_with_tls(port: int):
    pass


def run():
    network_conf = config.get_yml_config().network
    if network_conf.httpServer.enable:
        run_without_tls(network_conf.httpServer.port)
    elif network_conf.httpsServer.enable:
        run_with_tls(network_conf.httpsServer.port)
