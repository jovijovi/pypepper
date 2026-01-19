import pytest

from pypepper.scheduler.executor import Executor
from pypepper.scheduler.task import Task


def test_new_task():
    task = Task(
        channel_id='channel_1',
        dag_id='dag_1',
        fingerprint='fingerprint_1',
        name='Test Task',
        category='Test Category',
        description='This is a test task',
        tags=[],
        executor=Executor(),
        round_timeout=60,
        round_times=3,
        version=1,
        retry_count=2,
        retry_delay=5,
        retry_until_completed=True,
        optional=False
    )

    assert task is not None
    print("Task ID=", task.id)
    print("Task Context ID=", task.context.context_id)


if __name__ == '__main__':
    pytest.main()
