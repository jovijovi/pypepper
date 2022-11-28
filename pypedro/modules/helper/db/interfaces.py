from __future__ import annotations

from abc import ABCMeta


class IConfig(metaclass=ABCMeta):
    uri: str | None
    username: str | None
    password: str | None
    host: str | None
    port: int = 0
    db: str | None

    def __init__(self,
                 uri: str | None = None,
                 username: str | None = None,
                 password: str | None = None,
                 host: str | None = None,
                 port: int = 0,
                 db: str | None = None,
                 ):
        self.uri = uri
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.db = db
