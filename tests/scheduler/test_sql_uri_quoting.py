"""Unit tests: SQL job store assembles quoted discrete URIs."""

from urllib.parse import unquote_plus, urlsplit

from pypepper.helper.db.uri import build_mysql_uri, build_postgres_uri
from pypepper.scheduler.store import sql as sql_mod


def test_engine_from_config_postgres_uses_quoted_uri(monkeypatch):
    captured: list[str] = []

    def fake_create_engine(uri, *args, **kwargs):
        captured.append(uri)
        return object()

    monkeypatch.setattr(sql_mod, "create_engine", fake_create_engine)
    sql_mod._engine_from_config(
        "postgres",
        username="user@name",
        password="p#ass:w/ord",
        host="localhost",
        port=5432,
        db="app",
    )
    assert len(captured) == 1
    expected = build_postgres_uri(
        username="user@name",
        password="p#ass:w/ord",
        host="localhost",
        port=5432,
        db="app",
    )
    assert captured[0] == expected
    parts = urlsplit(captured[0])
    assert parts.fragment == ""
    assert unquote_plus(parts.password or "") == "p#ass:w/ord"


def test_engine_from_config_mysql_uses_quoted_uri(monkeypatch):
    captured: list[str] = []

    def fake_create_engine(uri, *args, **kwargs):
        captured.append(uri)
        return object()

    monkeypatch.setattr(sql_mod, "create_engine", fake_create_engine)
    sql_mod._engine_from_config(
        "mysql",
        username="u:ser",
        password="p@ss/word",
        host="127.0.0.1",
        port=3306,
        db="app",
        charset="utf8mb4",
    )
    assert captured == [
        build_mysql_uri(
            username="u:ser",
            password="p@ss/word",
            host="127.0.0.1",
            port=3306,
            db="app",
            charset="utf8mb4",
        )
    ]
