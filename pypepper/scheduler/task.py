from abc import ABCMeta

from pypepper.common.context import Context
from pypepper.common.utils import uuid
from pypepper.scheduler.base import IBase
from pypepper.scheduler.executor import Executor
from pypepper.scheduler.tag import Tag


class ITask(IBase, metaclass=ABCMeta):
    retry_count: int = 0
    retry_delay: int = 0
    retry_until_completed: bool = False
    optional: bool = False
    executor: Executor


class Task(ITask):
    def __init__(self,
                 channel_id: str,
                 dag_id: str,
                 fingerprint: str,
                 name: str,
                 category: str,
                 description: str,
                 tags: list[Tag],
                 executor: Executor,
                 round_timeout: int = 0,
                 round_times: int = 1,
                 version: int = 1,
                 retry_count: int = 0,
                 retry_delay: int = 0,
                 retry_until_completed: bool = False,
                 optional: bool = False,
                 ):
        self.channel_id = channel_id
        self.dag_id = dag_id
        self.fingerprint = fingerprint
        self.name = name
        self.category = category
        self.description = description
        self.tags = tags
        self.executor = executor
        self.round_timeout = round_timeout
        self.round_times = round_times
        self.version = version
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.retry_until_completed = retry_until_completed
        self.optional = optional
        self.id = uuid.new_uuid()
        self.context = Context(context_id=uuid.new_uuid())
