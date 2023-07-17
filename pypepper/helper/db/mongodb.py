from __future__ import annotations

from abc import ABCMeta

from mongoengine import connect as connect_db, disconnect_all

from pypepper.helper.db.interfaces import IConfig


class Config(IConfig, metaclass=ABCMeta):
    auth_source: str = 'admin'

    def __init__(self,
                 uri: str | None = None,
                 username: str | None = None,
                 password: str | None = None,
                 host: str | None = None,
                 port: int = 27017,
                 db: str | None = None,
                 auth_source: str = 'admin'):
        super().__init__(
            uri=uri,
            username=username,
            password=password,
            host=host,
            port=port,
            db=db,
        )
        self.auth_source = auth_source


def connect(cfg: Config) -> None:
    assert cfg, 'invalid database config'

    if cfg.uri:
        connect_db(host=cfg.uri)
    else:
        connect_db(
            username=cfg.username,
            password=cfg.password,
            host=cfg.host,
            port=cfg.port,
            db=cfg.db,
            authentication_source=cfg.auth_source,
        )


def close():
    disconnect_all()
