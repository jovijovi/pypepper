"""Job store interfaces and record model."""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class JobRecord:
    """Serializable job snapshot (metadata only; no executors)."""

    id: str
    category: str | None
    channel_id: str
    status: str
    created: str
    updated: str
    workflow_count: int = 0
    version: int = 1


class IJobStore(metaclass=ABCMeta):
    """Pluggable persistence for JobRecord snapshots."""

    @abstractmethod
    def put(self, record: JobRecord) -> None:
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
