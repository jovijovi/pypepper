"""FastAPI HTTP server run helpers (plain and TLS)."""

import ssl

import uvicorn
from fastapi import FastAPI

from pypepper.common.config import config
from pypepper.network.http.handlers import handlers
from pypepper.network.http.interfaces import ITaskHandler

# Compatibility shell only — never registered. Prefer :func:`create_app`.
# ``run`` / ``run_without_tls`` / ``run_with_tls`` ignore this object.
app = FastAPI()


def create_app(handlers_: ITaskHandler | None = None) -> FastAPI:
    """Build a new FastAPI app with handlers and middleware registered once."""
    application = FastAPI()
    handlers.register_handlers(application, handlers_)
    handlers.use_middleware(application, handlers_)
    return application


def run_without_tls(port: int, handlers_: ITaskHandler | None, host: str = "0.0.0.0") -> None:
    application = create_app(handlers_)
    uvicorn.run(application, host=host, port=port, timeout_keep_alive=30)


def run_with_tls(port: int, handlers_: ITaskHandler | None, host: str = "0.0.0.0") -> None:
    network_conf = config.get_yml_config().network
    https = network_conf.httpsServer
    cert_file = getattr(https, "certFile", None) or ""
    key_file = getattr(https, "keyFile", None) or ""
    ca_file = getattr(https, "caFile", None) or ""

    if not cert_file or not key_file:
        raise ValueError("HTTPS enabled but certFile/keyFile missing in network.httpsServer config")

    mutual_tls = bool(getattr(https, "mutualTLS", False))
    if mutual_tls and not ca_file:
        raise ValueError("HTTPS mutualTLS enabled but caFile missing in network.httpsServer config")

    application = create_app(handlers_)
    run_kwargs: dict = {
        "host": host,
        "port": port,
        "timeout_keep_alive": 30,
        "ssl_certfile": cert_file,
        "ssl_keyfile": key_file,
    }
    if mutual_tls:
        # CERT_REQUIRED: uvicorn defaults to CERT_NONE even when ca certs are set.
        run_kwargs["ssl_ca_certs"] = ca_file
        run_kwargs["ssl_cert_reqs"] = ssl.CERT_REQUIRED
    uvicorn.run(application, **run_kwargs)


def run(handlers_: ITaskHandler | None = None) -> None:
    network_conf = config.get_yml_config().network
    host = getattr(network_conf, "ip", None) or "0.0.0.0"
    if network_conf.httpServer.enable:
        run_without_tls(network_conf.httpServer.port, handlers_, host=host)
    elif network_conf.httpsServer.enable:
        run_with_tls(network_conf.httpsServer.port, handlers_, host=host)
    else:
        raise RuntimeError("Neither httpServer nor httpsServer is enabled in config")
