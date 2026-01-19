import pytest

from pypepper.scheduler.executor import Executor
from pypepper.scheduler.task import Task
from pypepper.scheduler.workflow import Workflow


def test_workflow():
    task_1 = Task(
        channel_id='channel_1',
        dag_id='dag_1',
        fingerprint='fingerprint_1',
        name='Test Task',
        category='Test Category',
        description='This is a test task',
        tags=[],
        executor=Executor(),
    )

    task_2 = Task(
        channel_id='channel_2',
        dag_id='dag_2',
        fingerprint='fingerprint_2',
        name='Another Test Task',
        category='Another Test Category',
        description='This is another test task',
        tags=[],
        executor=Executor(),
    )

    workflow = Workflow()

    # Run the empty workflow
    workflow.run()

    workflow.add_task(task_1)
    workflow.add_tasks([task_2])
    tasks = workflow.get_tasks()

    assert tasks is not None

    assert len(tasks) == 2
    print("Task Count=", len(tasks))

    assert tasks[0] == task_1
    print("Task 1 ID=", tasks[0].id)

    assert tasks[1] == task_2
    print("Task 2 ID=", tasks[1].id)

    # Run the workflow with tasks
    workflow.run()


if __name__ == '__main__':
    pytest.main()
