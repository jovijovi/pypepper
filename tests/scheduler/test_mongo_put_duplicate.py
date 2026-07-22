"""Unit tests for MongoJobStore.put DuplicateKeyError retry path."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pymongo.errors import DuplicateKeyError

from pypepper.scheduler.status import Status
from pypepper.scheduler.store.interfaces import JobRecord
from pypepper.scheduler.store.mongodb import MongoJobStore


def test_mongo_put_retries_set_only_on_duplicate_key(monkeypatch):
    store = object.__new__(MongoJobStore)
    store._alias = "test-alias"
    calls: list[tuple[dict, dict, bool]] = []

    def fake_update_one(filter_, update, upsert=False):
        calls.append((filter_, update, upsert))
        if len(calls) == 1:
            raise DuplicateKeyError("E11000 duplicate key")
        return SimpleNamespace(matched_count=1)

    collection = MagicMock()
    collection.update_one.side_effect = fake_update_one

    class _Switch:
        def __enter__(self):
            return None

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "pypepper.scheduler.store.mongodb.switch_db",
        lambda *a, **k: _Switch(),
    )
    monkeypatch.setattr(
        "pypepper.scheduler.store.mongodb.SchedulerJobDoc._get_collection",
        classmethod(lambda cls: collection),
    )

    record = JobRecord(
        id="dup-1",
        category="c",
        channel_id="ch",
        status=Status.SCHEDULED.value,
        created="t0",
        updated="t1",
        workflow_count=1,
        version=1,
    )
    store.put(record)

    assert len(calls) == 2
    assert calls[0][2] is True
    assert "$setOnInsert" in calls[0][1]
    assert calls[0][1]["$setOnInsert"]["created"] == "t0"
    assert calls[1][2] is False
    assert calls[1][1] == {
        "$set": {
            "category": "c",
            "channel_id": "ch",
            "status": Status.SCHEDULED.value,
            "updated": "t1",
            "workflow_count": 1,
            "version": 1,
        }
    }
    assert "created" not in calls[1][1]["$set"]


def test_mongo_put_raises_if_missing_after_duplicate_key(monkeypatch):
    store = object.__new__(MongoJobStore)
    store._alias = "test-alias"

    def fake_update_one(filter_, update, upsert=False):
        if upsert:
            raise DuplicateKeyError("E11000")
        return SimpleNamespace(matched_count=0)

    collection = MagicMock()
    collection.update_one.side_effect = fake_update_one

    class _Switch:
        def __enter__(self):
            return None

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "pypepper.scheduler.store.mongodb.switch_db",
        lambda *a, **k: _Switch(),
    )
    monkeypatch.setattr(
        "pypepper.scheduler.store.mongodb.SchedulerJobDoc._get_collection",
        classmethod(lambda cls: collection),
    )

    record = JobRecord(
        id="gone",
        category="c",
        channel_id="ch",
        status=Status.SCHEDULED.value,
        created="t0",
        updated="t1",
        workflow_count=1,
        version=1,
    )
    with pytest.raises(RuntimeError, match="missing after DuplicateKeyError"):
        store.put(record)
