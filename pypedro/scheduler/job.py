from abc import ABCMeta

from pypedro.scheduler.base import IBase
from pypedro.scheduler.workflow import Workflow


class IJob(IBase, metaclass=ABCMeta):
    workflows: list[Workflow]
