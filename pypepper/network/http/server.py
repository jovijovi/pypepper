import uvicorn
from fastapi import FastAPI

from pypepper.common.config import config
from pypepper.network.http.handlers import handlers
from pypepper.network.http.interfaces import ITaskHandler

app = FastAPI()


def run_without_tls(port: int, handlers_: ITaskHandler | None, host: str = "0.0.0.0"):
    handlers.register_handlers(app, handlers_)
    handlers.use_middleware(app, handlers_)
    uvicorn.run(app, host=host, port=port, timeout_keep_alive=30)


def run_with_tls(port: int, handlers_: ITaskHandler | None, host: str = "0.0.0.0"):
    network_conf = config.get_yml_config().network
    https = network_conf.httpsServer
    cert_file = getattr(https, "certFile", None) or ""
    key_file = getattr(https, "keyFile", None) or ""
    ca_file = getattr(https, "caFile", None) or ""

    if not cert_file or not key_file:
        raise ValueError("HTTPS enabled but certFile/keyFile missing in network.httpsServer config")

    handlers.register_handlers(app, handlers_)
    handlers.use_middleware(app, handlers_)

    if getattr(https, "mutualTLS", False) and ca_file:
        uvicorn.run(
            app,
            host=host,
            port=port,
            timeout_keep_alive=30,
            ssl_certfile=cert_file,
            ssl_keyfile=key_file,
            ssl_ca_certs=ca_file,
        )
    else:
        uvicorn.run(
            app,
            host=host,
            port=port,
            timeout_keep_alive=30,
            ssl_certfile=cert_file,
            ssl_keyfile=key_file,
        )


def run(handlers_: ITaskHandler | None = None):
    network_conf = config.get_yml_config().network
    host = getattr(network_conf, "ip", None) or "0.0.0.0"
    if network_conf.httpServer.enable:
        run_without_tls(network_conf.httpServer.port, handlers_, host=host)
    elif network_conf.httpsServer.enable:
        run_with_tls(network_conf.httpsServer.port, handlers_, host=host)
    else:
        raise RuntimeError("Neither httpServer nor httpsServer is enabled in config")
