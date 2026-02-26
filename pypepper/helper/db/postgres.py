from __future__ import annotations

from abc import ABCMeta

from sqlalchemy import create_engine, Connection

from pypepper.helper.db.interfaces import IConfig


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
    assert cfg, 'invalid database config'

    if cfg.uri:
        return create_engine(cfg.uri).connect()

    assert cfg.username, 'invalid username'
    assert cfg.password, 'invalid password'
    assert cfg.host, 'invalid host'
    assert cfg.db, 'invalid db'

    uri = f'postgresql+psycopg://{cfg.username}:{cfg.password}@{cfg.host}:{cfg.port}/{cfg.db}'
    if cfg.sslmode:
        uri = f'{uri}?sslmode={cfg.sslmode}'
    return create_engine(uri).connect()


def ping(engine: Connection) -> bool:
    assert engine, 'invalid engine'
    return not engine.closed
