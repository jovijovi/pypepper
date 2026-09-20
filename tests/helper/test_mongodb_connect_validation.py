"""Unit tests for helper MongoDB connect validation (no running server required)."""

import pytest
from pypepper.helper.db import mongodb


def test_mongodb_connect_requires_uri_or_discrete_fields():
    with pytest.raises(ValueError, match="uri=... or username, password, host, and db"):
        mongodb.connect(mongodb.Config(host="localhost"))


def test_mongodb_connect_rejects_empty_config():
    with pytest.raises(ValueError, match="invalid database config"):
        mongodb.connect(None)  # type: ignore[arg-type]


def test_mongodb_connect_uses_discrete_fields(monkeypatch):
    captured: dict[str, object] = {}

    def fake_connect_db(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(mongodb, "connect_db", fake_connect_db)
    mongodb.connect(
        mongodb.Config(
            username="u",
            password="p",
            host="localhost",
            port=27018,
            db="app",
            auth_source="admin",
        )
    )
    assert captured == {
        "username": "u",
        "password": "p",
        "host": "localhost",
        "port": 27018,
        "db": "app",
        "authentication_source": "admin",
        "uuidRepresentation": "standard",
    }
