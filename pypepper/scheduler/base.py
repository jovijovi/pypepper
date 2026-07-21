from __future__ import annotations

from abc import ABCMeta

from pypepper.common.context import Context
from pypepper.scheduler.tag import Tag


class IBase(metaclass=ABCMeta):
    id: str
    channel_id: str
    dag_id: str
    fingerprint: str
    name: str
    category: str | None
    description: str
    status: str
    created: str
    updated: str
    tags: list[Tag]
    progress: float = 0
    # Seconds per execute attempt when wired by Workflow (0 = no timeout).
    round_timeout: int = 0
    # Outer execution rounds per task (each round has its own retry budget).
    round_times: int = 1
    version: int = 1
    context: Context
