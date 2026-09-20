"""Job store interfaces and record model."""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JobRecord:
    """Job snapshot. Executors are omitted unless ``payload`` is present."""

    id: str
    category: str | None
    channel_id: str
    status: str
    created: str
    updated: str
    workflow_count: int = 0
    version: int = 1
    payload: dict[str, Any] | None = None


class IJobStore(metaclass=ABCMeta):
    """Pluggable persistence for JobRecord snapshots."""

    @abstractmethod
    def put(self, record: JobRecord) -> bool:
        """
        Upsert by ``id``.

        Returns ``True`` when the row is inserted or updated, ``False`` when the
        write is skipped (lifecycle fence or version conflict).

        Must not overwrite an existing row's ``created``. Must not replace a
        durable status with an earlier lifecycle (for example Scheduled must
        not overwrite InProgress/Completed/Failed/Cancelled). Distinct
        terminals must not overwrite each other. Same status may update other
        fields. Updates require ``record.version`` to equal the durable version
        (then the stored version is incremented).
        """
        pass

    @abstractmethod
    def get(self, job_id: str) -> JobRecord | None:
        pass

    @abstractmethod
    def delete(self, job_id: str) -> None:
        pass

    @abstractmethod
    def list(self, channel_id: str | None = None) -> list[JobRecord]:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass
