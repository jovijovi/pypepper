from abc import ABCMeta

from pypepper.scheduler.base import IBase
from pypepper.scheduler.task import Task


class IWorkflow(IBase, metaclass=ABCMeta):
    tasks: list[Task]


class Workflow(IWorkflow):
    def add_task(self, task: Task):
        self.tasks.append(task)

    def add_tasks(self, tasks: list[Task]):
        self.tasks.extend(tasks)

    def get_tasks(self) -> list[Task]:
        return self.tasks

    def run(self):
        # TODO:
        if len(self.tasks) == 0:
            return
