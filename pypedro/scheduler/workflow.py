from abc import ABCMeta

from pypedro.scheduler.base import IBase
from pypedro.scheduler.task import Task


class IWorkflow(IBase, metaclass=ABCMeta):
    tasks: list[Task]


class Workflow(IWorkflow):
    pass
