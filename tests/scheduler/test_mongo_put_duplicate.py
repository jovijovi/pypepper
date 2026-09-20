"""Unit tests for MongoJobStore.put DuplicateKeyError retry path."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pymongo.errors import DuplicateKeyError
from pypepper.scheduler.status import Status
from pypepper.scheduler.store.interfaces import JobRecord
from pypepper.scheduler.store.mongodb import MongoJobStore


def _record(*, job_id: str = "dup-1") -> JobRecord:
    return JobRecord(
        id=job_id,
        category="c",
        channel_id="ch",
        status=Status.SCHEDULED.value,
        created="t0",
        updated="t1",
        workflow_count=1,
        version=1,
    )


class _Switch:
    def __enter__(self):
        return None

    def __exit__(self, *args):
        return False


def _patch_collection(monkeypatch, collection: MagicMock) -> MongoJobStore:
    store = object.__new__(MongoJobStore)
    store._alias = "test-alias"
    monkeypatch.setattr(
        "pypepper.scheduler.store.mongodb.switch_db",
        lambda *a, **k: _Switch(),
    )
    monkeypatch.setattr(
        "pypepper.scheduler.store.mongodb.SchedulerJobDoc._get_collection",
        classmethod(lambda cls: collection),
    )
    return store


def test_mongo_put_inserts_when_absent(monkeypatch):
    collection = MagicMock()
    collection.update_one.return_value = SimpleNamespace(matched_count=0)
    collection.insert_one.return_value = SimpleNamespace(inserted_id="dup-1")

    store = _patch_collection(monkeypatch, collection)
    assert store.put(_record()) is True
    collection.insert_one.assert_called_once()
    assert collection.update_one.call_count == 1
    assert collection.update_one.call_args.kwargs.get("upsert") is False


def test_mongo_put_retries_set_only_on_duplicate_key(monkeypatch):
    calls: list[tuple[dict, dict, bool]] = []

    def fake_update_one(filter_, update, upsert=False):
        calls.append((filter_, update, upsert))
        if len(calls) == 1:
            return SimpleNamespace(matched_count=0)
        return SimpleNamespace(matched_count=1)

    collection = MagicMock()
    collection.update_one.side_effect = fake_update_one
    collection.insert_one.side_effect = DuplicateKeyError("E11000 duplicate key")

    store = _patch_collection(monkeypatch, collection)
    assert store.put(_record()) is True

    assert collection.insert_one.call_count == 1
    inserted = collection.insert_one.call_args.args[0]
    assert inserted["_id"] == "dup-1"
    assert inserted["created"] == "t0"
    assert len(calls) == 2
    assert calls[0][2] is False
    assert calls[0][0]["_id"] == "dup-1"
    assert "$in" in calls[0][0]["status"]
    assert calls[1][2] is False
    assert calls[0][0]["version"] == 1
    assert calls[1][1] == {
        "$set": {
            "category": "c",
            "channel_id": "ch",
            "status": Status.SCHEDULED.value,
            "updated": "t1",
            "workflow_count": 1,
            "version": 2,
            "payload": None,
        }
    }
    assert "created" not in calls[1][1]["$set"]


def test_mongo_put_raises_if_missing_after_duplicate_key(monkeypatch):
    collection = MagicMock()
    collection.update_one.return_value = SimpleNamespace(matched_count=0)
    collection.insert_one.side_effect = DuplicateKeyError("E11000")
    collection.find_one.return_value = None

    store = _patch_collection(monkeypatch, collection)
    with pytest.raises(RuntimeError, match="missing after DuplicateKeyError"):
        store.put(_record(job_id="gone"))


def test_mongo_put_skips_downgrade_after_duplicate_key(monkeypatch):
    collection = MagicMock()
    collection.update_one.return_value = SimpleNamespace(matched_count=0)
    collection.insert_one.side_effect = DuplicateKeyError("E11000")
    collection.find_one.return_value = {"_id": "ahead", "status": Status.COMPLETED.value}

    store = _patch_collection(monkeypatch, collection)
    assert store.put(_record(job_id="ahead")) is False
    collection.find_one.assert_called_once_with({"_id": "ahead"})
