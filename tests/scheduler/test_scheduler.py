import time

import pytest

from pypepper.scheduler import events
from pypepper.scheduler.events import FSM
from pypepper.scheduler.job import Job


def test_scheduler():
    for i in range(10):
        job = Job('Foo')
        job.channel_id = 'bar'
        job.scheduled()
    time.sleep(1)


def test_status():
    try:
        machine = FSM()

        status1 = machine.on(events.INIT)
        print("Status=", status1.state.value)

        status1 = machine.on(events.INIT)
        assert status1.error
        print("Error=", status1.error)

        status1 = machine.on(events.SCHEDULE)
        print("Status=", status1.state.value)

        status1 = machine.on(events.RUN)
        print("Status=", status1.state.value)

        status1 = machine.on(events.COMPLETE)
        print("Status=", status1.state.value)

        status1 = machine.on(events.FAIL)
        assert status1.error
        print("Error=", status1.error)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    pytest.main()
