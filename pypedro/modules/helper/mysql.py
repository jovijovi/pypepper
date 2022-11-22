from __future__ import annotations

from abc import ABCMeta

from sqlalchemy import create_engine, Connection


class Config(metaclass=ABCMeta):
    uri: str | None
    username: str | None
    password: str | None
    host: str | None
    port: int = 3306
    db: str | None
    charset: str = 'utf8mb4'

    def __init__(self,
                 uri: str | None = None,
                 username: str | None = None,
                 password: str | None = None,
                 host: str | None = None,
                 port: int = 3306,
                 db: str | None = None,
                 charset: str = 'utf8mb4',
                 ):
        self.uri = uri
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.db = db
        self.charset = charset


def connect(cfg: Config) -> Connection:
    assert cfg, 'invalid database config'

    if cfg.uri:
        return create_engine(cfg.uri).connect()

    assert cfg.username, 'invalid username'
    assert cfg.password, 'invalid password'
    assert cfg.host, 'invalid host'
    assert cfg.db, 'invalid db'

    uri = f'mysql+pymysql://{cfg.username}:{cfg.password}@{cfg.host}:{cfg.port}/{cfg.db}?charset={cfg.charset}'
    return create_engine(uri).connect()


def ping(engine: Connection) -> bool:
    assert engine, 'invalid engine'
    return not engine.closed
