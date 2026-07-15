"""PostgreSQL SQLAlchemy connector helper."""

from __future__ import annotations

from abc import ABCMeta

from sqlalchemy import Connection, create_engine

from pypepper.helper.db.interfaces import IConfig
from pypepper.helper.db.uri import build_postgres_uri


class Config(IConfig, metaclass=ABCMeta):
    sslmode: str | None = None

    def __init__(
        self,
        uri: str | None = None,
        username: str | None = None,
        password: str | None = None,
        host: str | None = None,
        port: int = 5432,
        db: str | None = None,
        sslmode: str | None = None,
    ):
        super().__init__(
            uri=uri,
            username=username,
            password=password,
            host=host,
            port=port,
            db=db,
        )
        self.sslmode = sslmode


def connect(cfg: Config) -> Connection:
    if not cfg:
        raise ValueError("invalid database config")

    if cfg.uri:
        return create_engine(cfg.uri).connect()

    if not cfg.username:
        raise ValueError("invalid username")
    if not cfg.password:
        raise ValueError("invalid password")
    if not cfg.host:
        raise ValueError("invalid host")
    if not cfg.db:
        raise ValueError("invalid db")

    uri = build_postgres_uri(
        username=cfg.username,
        password=cfg.password,
        host=cfg.host,
        port=cfg.port,
        db=cfg.db,
        sslmode=cfg.sslmode,
    )
    return create_engine(uri).connect()


def ping(engine: Connection) -> bool:
    if not engine:
        raise ValueError("invalid engine")
    return not engine.closed
