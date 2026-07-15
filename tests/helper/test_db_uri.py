"""Unit tests for SQLAlchemy URI builders (credential quoting)."""

from urllib.parse import unquote_plus, urlsplit

from pypepper.helper.db.uri import build_mysql_uri, build_postgres_uri


def test_build_postgres_uri_quotes_special_password():
    uri = build_postgres_uri(
        username="user@name",
        password="p@ss:w/ord",
        host="localhost",
        port=5432,
        db="app",
    )
    parts = urlsplit(uri)
    assert parts.scheme == "postgresql+psycopg"
    assert parts.hostname == "localhost"
    assert parts.port == 5432
    assert parts.path == "/app"
    assert unquote_plus(parts.username or "") == "user@name"
    assert unquote_plus(parts.password or "") == "p@ss:w/ord"


def test_build_postgres_uri_quotes_hash_and_plus():
    uri = build_postgres_uri(
        username="u+name",
        password="a#b+c",
        host="localhost",
        port=5432,
        db="app",
    )
    parts = urlsplit(uri)
    assert parts.fragment == ""
    assert unquote_plus(parts.username or "") == "u+name"
    assert unquote_plus(parts.password or "") == "a#b+c"
    assert "%23" in (parts.password or "")
    assert "%2B" in (parts.username or "") or "%2B" in (parts.password or "")


def test_build_postgres_uri_sslmode_query():
    uri = build_postgres_uri(
        username="u",
        password="p",
        host="db.example",
        port=5432,
        db="app",
        sslmode="require",
    )
    assert uri.endswith("?sslmode=require")


def test_build_postgres_uri_omits_query_without_sslmode():
    uri = build_postgres_uri(
        username="u",
        password="p",
        host="db.example",
        port=5432,
        db="app",
    )
    assert "?" not in uri


def test_build_mysql_uri_quotes_special_password():
    uri = build_mysql_uri(
        username="u:ser",
        password="p@ss/word",
        host="127.0.0.1",
        port=3306,
        db="app",
        charset="utf8mb4",
    )
    parts = urlsplit(uri)
    assert parts.scheme == "mysql+pymysql"
    assert parts.hostname == "127.0.0.1"
    assert parts.port == 3306
    assert parts.path == "/app"
    assert "charset=utf8mb4" in (parts.query or "")
    assert unquote_plus(parts.username or "") == "u:ser"
    assert unquote_plus(parts.password or "") == "p@ss/word"
