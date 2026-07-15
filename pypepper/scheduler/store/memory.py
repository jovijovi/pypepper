"""In-memory JobStore (default / tests)."""

from __future__ import annotations

from dataclasses import replace
from threading import Lock

from pypepper.scheduler.store.interfaces import IJobStore, JobRecord


class InMemoryJobStore(IJobStore):
    """Thread-safe dict-backed job store."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._store: dict[str, JobRecord] = {}

    def put(self, record: JobRecord) -> None:
        with self._lock:
            existing = self._store.get(record.id)
            if existing is not None:
                record = replace(record, created=existing.created)
            self._store[record.id] = record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._store.get(job_id)

    def delete(self, job_id: str) -> None:
        with self._lock:
            self._store.pop(job_id, None)

    def list(self, channel_id: str | None = None) -> list[JobRecord]:
        with self._lock:
            records = list(self._store.values())
        if channel_id is None:
            return records
        return [r for r in records if r.channel_id == channel_id]

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
