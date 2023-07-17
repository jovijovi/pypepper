from abc import ABCMeta

from pypepper.common.context import Context
from pypepper.scheduler.tag import Tag


class IBase(metaclass=ABCMeta):
    id: str
    channel_id: str
    dag_id: str
    fingerprint: str
    name: str
    category: str
    description: str
    status: str
    created: str
    updated: str
    tags: list[Tag]
    progress: float = 0
    round_timeout: int = 0
    round_times: int = 1
    version: int = 1
    context: Context
