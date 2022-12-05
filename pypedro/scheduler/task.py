from abc import ABCMeta

from pypedro.scheduler.base import IBase
from pypedro.scheduler.executor import Executor


class ITask(IBase, metaclass=ABCMeta):
    retry_count: int = 0
    retry_delay: int = 0
    retry_until_completed: bool = False
    optional: bool = False
    executor: Executor


class Task(ITask):
    pass
