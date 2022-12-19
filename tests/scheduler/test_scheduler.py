import time

import pytest

from pypedro.scheduler.job import Job


def test_scheduler():
    for i in range(10):
        job = Job('Foo')
        job.channel_id = 'bar'
        job.scheduled()
    time.sleep(1)


if __name__ == '__main__':
    pytest.main()
