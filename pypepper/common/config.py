import argparse
import os.path
from typing import Any

import yaml
from box import Box

from pypepper.common.log import log


class ConfCluster:
    name: str
    id: str
    description: str


class ConfHTTPServer:
    enable: bool
    port: int
    timeout: int = 30


class ConfHTTPSServer:
    enable: bool
    port: int
    mutualTLS: bool
    timeout: int = 30


class ConfHeartbeat:
    enable: bool
    port: int
    logger: bool


class ConfJsonRPCProxy:
    enable: bool
    port: int
    mutualTLS: bool


class ConfNetwork:
    ip: str
    httpServer: ConfHTTPServer
    httpsServer: ConfHTTPSServer
    jsonRPCProxy: ConfJsonRPCProxy


class ConfLog:
    mode: str
    level: str
    colorize: bool


class YmlConfig:
    cluster: ConfCluster
    network: ConfNetwork
    heartbeat: ConfHeartbeat
    log: ConfLog
    custom: Any


class Config:
    _default_config_path = './conf/'
    _default_config_filename = 'app.config.yaml'
    _default_config_filepath = os.path.join(_default_config_path, _default_config_filename)
    _setting: Any = None

    def __init__(self):
        pass

    def _get_parser(self, **parser_kwargs):
        parser = argparse.ArgumentParser(**parser_kwargs)
        parser.add_argument(
            '-c',
            '--config',
            type=str,
            const=True,
            default=os.path.join(self._default_config_filepath),
            nargs='?',
            help='config filename & path',
        )
        return parser

    def load_config(self, filename: str = None):
        if filename:
            service_config_filename = os.path.abspath(filename)
        else:
            parser = self._get_parser()
            args = parser.parse_args()
            if args.config:
                service_config_filename = args.config
            else:
                service_config_filename = os.path.abspath(self._default_config_filepath)

        with open(service_config_filename, 'r') as fd:
            data = fd.read()
        self._setting = Box(yaml.safe_load(data))

        # Set log config (level, colorize...)
        if hasattr(self.get_yml_config(), "log") and hasattr(self.get_yml_config().log, "level"):
            log.set_log_level(self.get_yml_config().log.level)
            log.set_colorize(self.get_yml_config().log.colorize)

    def get_yml_config(self) -> YmlConfig:
        return self._setting


config = Config()
