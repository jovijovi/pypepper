import pytest

from pedro.event import event
from pedro.fsm import fsm
from pedro.fsm.fsm import Transition


def test_new_state():
    state = fsm.new_state('Closed')
    print("State=", state.value)
    state.value = 'Opened'
    print("State=", state.value)


def test_fsm():
    evt1 = event.new()
    evt1.set_name('OpenDoor')
    evt1.set_src('Closed')

    evt2 = event.new()
    evt2.set_name('CloseDoor')
    evt2.set_src('Opened')

    evt3 = event.new()
    evt3.set_name('Knock Knock')
    evt3.set_src('Closed')

    options = fsm.Options(
        fsm_id='test-id-1',
        initial=fsm.new_state('Closed'),
        transitions=[
            Transition(
                event=evt1,
                from_state=[fsm.new_state('Closed')],
                to_state=fsm.new_state('Opened'),
                handler=None,
                context=None,
            ),
            Transition(
                event=evt2,
                from_state=[fsm.new_state('Opened')],
                to_state=fsm.new_state('Closed'),
                handler=None,
                context=None,
            )
        ]
    )
    machine = fsm.new(options)

    print("Initial state=", machine.current().value)

    rsp1 = machine.on(evt1, lambda: print(f'Event({evt1.data.name}) finished'))
    print("Error1=", rsp1.error)
    print("Current state1=", rsp1.state.value)

    rsp2 = machine.on(evt2, lambda: print(f'Event({evt2.data.name}) finished'))
    print("Error2=", rsp2.error)
    print("Current state2=", rsp2.state.value)

    rsp3 = machine.on(evt3)
    print("Error3=", rsp3.error)
    print("Current state3=", rsp3.state.value)

    def mock_error():
        raise Exception('Mock Error!')

    rsp4 = machine.on(evt1, lambda: mock_error())
    print("Error4=", rsp4.error)
    print("Current state4=", rsp4.state.value)


if __name__ == '__main__':
    pytest.main()
