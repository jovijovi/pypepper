"""Unit tests for SQL job-store payload JSON helpers and schema migrate."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from pypepper.scheduler.store import sql as sql_mod


def test_dumps_payload_none_and_dict():
    assert sql_mod._dumps_payload(None) is None
    assert json.loads(sql_mod._dumps_payload({"a": 1}) or "") == {"a": 1}


def test_loads_payload_empty_dict_and_non_dict():
    assert sql_mod._loads_payload(None) is None
    assert sql_mod._loads_payload("") is None
    assert sql_mod._loads_payload(json.dumps({"k": "v"})) == {"k": "v"}
    assert sql_mod._loads_payload(json.dumps([1, 2])) is None


def test_ensure_schema_returns_when_table_missing(monkeypatch):
    engine = MagicMock()
    inspector = MagicMock()
    inspector.get_table_names.return_value = []
    monkeypatch.setattr(sql_mod, "inspect", lambda _engine: inspector)
    monkeypatch.setattr(sql_mod._metadata, "create_all", lambda _engine: None)

    sql_mod._ensure_schema(engine)

    inspector.get_columns.assert_not_called()
    engine.begin.assert_not_called()


def test_ensure_schema_adds_payload_column_when_missing(monkeypatch):
    engine = MagicMock()
    conn = MagicMock()
    begin_cm = MagicMock()
    begin_cm.__enter__.return_value = conn
    begin_cm.__exit__.return_value = False
    engine.begin.return_value = begin_cm

    inspector = MagicMock()
    inspector.get_table_names.return_value = [sql_mod.TABLE_NAME]
    inspector.get_columns.return_value = [{"name": "id"}, {"name": "status"}]
    monkeypatch.setattr(sql_mod, "inspect", lambda _engine: inspector)
    monkeypatch.setattr(sql_mod._metadata, "create_all", lambda _engine: None)

    sql_mod._ensure_schema(engine)

    conn.execute.assert_called_once()
    clause = conn.execute.call_args[0][0]
    assert "payload" in str(getattr(clause, "text", clause)).lower()
