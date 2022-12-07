from abc import ABCMeta

from pypedro.scheduler.base import IBase
from pypedro.scheduler.channel import manager
from pypedro.scheduler.scheduler import scheduler
from pypedro.scheduler.workflow import Workflow


class IJob(IBase, metaclass=ABCMeta):
    workflows: list[Workflow]


class Job(IJob):
    def push(self):
        # TODO: job status FSM

        # TODO: save job
        self.save()
        # TODO: print log
        self.log()

        chan = manager.available(self.channel_id)
        scheduler.dispatch(
            job=self,
            chan=chan,
        )

        # TODO: scheduler

    def save(self):
        pass

    def log(self):
        pass


def new() -> Job:
    return Job()
