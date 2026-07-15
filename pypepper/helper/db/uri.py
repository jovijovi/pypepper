"""Build SQLAlchemy database URIs with quoted credentials."""

from __future__ import annotations

from urllib.parse import quote_plus


def _quote_userinfo(username: str, password: str) -> tuple[str, str]:
    return quote_plus(username), quote_plus(password)


def build_postgres_uri(
    *,
    username: str,
    password: str,
    host: str,
    port: int,
    db: str,
    sslmode: str | None = None,
) -> str:
    """Assemble a ``postgresql+psycopg`` URI with ``quote_plus`` on user/password."""
    user, pwd = _quote_userinfo(username, password)
    uri = f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{db}"
    if sslmode:
        return f"{uri}?sslmode={sslmode}"
    return uri


def build_mysql_uri(
    *,
    username: str,
    password: str,
    host: str,
    port: int,
    db: str,
    charset: str = "utf8mb4",
) -> str:
    """Assemble a ``mysql+pymysql`` URI with ``quote_plus`` on user/password."""
    user, pwd = _quote_userinfo(username, password)
    return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset={charset}"
