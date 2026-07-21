"""YAML config loading and typed configuration models."""

import argparse
import os.path
from typing import Any

import yaml
from box import Box

from pypepper.common.log import log


class ConfHTTPServer:
    enable: bool
    port: int


class ConfHTTPSServer:
    enable: bool
    port: int
    mutualTLS: bool
    certFile: str = ""
    keyFile: str = ""
    caFile: str = ""


class ConfNetwork:
    ip: str
    httpServer: ConfHTTPServer
    httpsServer: ConfHTTPSServer


class ConfLog:
    level: str
    colorize: bool


class ConfSSEAuthentication:
    enabled: bool
    validKeys: list


class ConfSSERateLimit:
    enabled: bool
    maxRequestsPerMinute: int


class ConfSSE:
    maxTotalConnections: int
    maxConnectionsPerIP: int
    maxQueueSize: int
    streamTimeoutSeconds: int
    authentication: ConfSSEAuthentication
    rateLimit: ConfSSERateLimit


class ConfTracingOTLP:
    enabled: bool
    endpoint: str


class ConfTracing:
    enabled: bool
    serviceName: str
    console: bool
    otlp: ConfTracingOTLP


class ConfSchedulerJobStore:
    backend: str
    uri: str | None
    host: str | None
    port: int | None
    username: str | None
    password: str | None
    db: str | None
    sslmode: str | None
    charset: str | None
    auth_source: str | None


class ConfScheduler:
    jobStore: ConfSchedulerJobStore


class YmlConfig:
    network: ConfNetwork
    log: ConfLog
    sse: ConfSSE
    tracing: ConfTracing
    scheduler: ConfScheduler
    custom: Any


class Config:
    _default_config_path = "./conf/"
    _default_config_filename = "app.config.yaml"
    _default_config_filepath = os.path.join(_default_config_path, _default_config_filename)

    def __init__(self) -> None:
        self._setting: Any = None
        self._deferred_durable_job_store_backend: str | None = None

    def _get_parser(self, **parser_kwargs):
        parser = argparse.ArgumentParser(**parser_kwargs)
        parser.add_argument(
            "-c",
            "--config",
            type=str,
            const=True,
            default=os.path.join(self._default_config_filepath),
            nargs="?",
            help="config filename & path",
        )
        return parser

    def load_config(self, filename: str | None = None):
        if filename:
            service_config_filename = os.path.abspath(filename)
        else:
            parser = self._get_parser()
            args = parser.parse_args()
            service_config_filename = args.config or os.path.abspath(self._default_config_filepath)

        with open(service_config_filename) as fd:
            data = fd.read()
        self._setting = Box(yaml.safe_load(data))

        # Set log config (level, colorize...)
        if hasattr(self.get_yml_config(), "log") and hasattr(self.get_yml_config().log, "level"):
            log.set_log_level(self.get_yml_config().log.level)
            log.set_colorize(self.get_yml_config().log.colorize)

        from pypepper.common.tracing import setup_from_config

        setup_from_config(self.get_yml_config())
        self.refresh_scheduler_job_store_deferred()

    def refresh_scheduler_job_store_deferred(self) -> None:
        """
        Re-read durable ``scheduler.jobStore`` from the current YAML into the deferred flag.

        Counterpart to :meth:`mark_scheduler_job_store_applied` (used by ``reset_job_store``
        and ``load_config``). Memory / missing backends clear the flag.
        """
        self._deferred_durable_job_store_backend = None
        yml = self.get_yml_config()
        if yml is None or not hasattr(yml, "scheduler") or yml.scheduler is None:
            return
        job_store = getattr(yml.scheduler, "jobStore", None)
        if job_store is None:
            return
        backend = getattr(job_store, "backend", None)
        if backend is None:
            return
        name = str(backend).strip().lower()
        if name in ("", "memory"):
            return
        self._deferred_durable_job_store_backend = str(backend)

    def mark_scheduler_job_store_applied(self) -> None:
        """Clear the deferred durable jobStore flag (called after setup/configure)."""
        self._deferred_durable_job_store_backend = None

    def ensure_scheduler_job_store_applied(self, *, using_default_memory_store: bool = True) -> None:
        """
        Raise if YAML declared a durable jobStore that has not been applied yet.

        When a non-memory store is already installed (``using_default_memory_store=False``),
        treat the deferred declaration as satisfied so configure-before-load and reload
        after setup do not false-positive.
        """
        backend = self._deferred_durable_job_store_backend
        if backend is None:
            return
        if not using_default_memory_store:
            self.mark_scheduler_job_store_applied()
            return
        raise ValueError(
            f"scheduler.jobStore.backend={backend!r} is present in YAML but not applied by "
            "load_config; call pypepper.scheduler.store.setup_from_config(...) after load "
            "before persisting jobs"
        )

    def get_yml_config(self) -> YmlConfig:
        return self._setting


config = Config()
