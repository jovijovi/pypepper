import pytest

from pypepper import errors
from pypepper.event import event
from pypepper.fsm import fsm


def test_new_state():
    state = fsm.State('Closed')
    print("State=", state.value)
    assert state.value == 'Closed'

    state.value = 'Opened'
    print("State=", state.value)
    assert state.value == 'Opened'


def test_fsm():
    # New event 1
    evt1 = event.new()
    evt1.set_name('OpenDoor')
    evt1.set_src('Closed')
    assert evt1
    assert evt1.data.name == 'OpenDoor'
    assert evt1.data.src == 'Closed'

    # New event 2
    evt2 = event.new()
    evt2.set_name('CloseDoor')
    evt2.set_src('Opened')
    assert evt2
    assert evt2.data.name == 'CloseDoor'
    assert evt2.data.src == 'Opened'

    # New event 3
    evt3 = event.new()
    evt3.set_name('Knock Knock')
    evt3.set_src('Closed')
    assert evt3
    assert evt3.data.name == 'Knock Knock'
    assert evt3.data.src == 'Closed'

    # Define an event handler
    def event2_handler():
        print("Event2 transition's handler: somebody close the door")
        return "#42#"

    # Build FSM options
    options = fsm.Options(
        fsm_id='test-id-1',
        initial=fsm.State('Closed'),
        transitions=[
            fsm.Transition(
                event=evt1,
                from_state=[fsm.State('Closed')],
                to_state=fsm.State('Opened'),
                handler=lambda ctx: print("Event1 transition's handler:", ctx.get('who'), ctx.get('what')),
                context={
                    'who': 'Door',
                    'what': 'opened',
                },
            ),
            fsm.Transition(
                event=evt2,
                from_state=[fsm.State('Opened')],
                to_state=fsm.State('Closed'),
                handler=lambda: event2_handler(),
                context=None,
            )
        ]
    )
    assert options
    assert options.fsm_id == 'test-id-1'
    assert options.initial.value == 'Closed'
    assert len(options.transitions) == 2

    # New an FSM
    machine = fsm.new(options)
    assert machine
    print("Initial state=", machine.current().value)
    assert machine.current().value == 'Closed'

    # Open the door
    rsp1 = machine.on(evt1, lambda: print(f'Event({evt1.data.name}) finished'))
    print("Error1=", rsp1.error)
    assert rsp1.error is None
    print("Current state1=", rsp1.state.value)
    assert rsp1.state.value == 'Opened'

    # Close the door
    rsp2 = machine.on(
        event=evt2,
        handler=lambda ctx: print(ctx.get("who"), ctx.get("what"), ":", "Hello, world!"),
        context={
            'who': 'Somebody',
            'what': 'say',
        }
    )
    print("Error2=", rsp2.error)
    assert rsp2.error is None
    print("Event handler result=", rsp2.event_handler_result)
    assert rsp2.event_handler_result == '#42#'
    print("Current state2=", rsp2.state.value)
    assert rsp2.state.value == 'Closed'

    # Knock Knock
    rsp3 = machine.on(evt3)
    print("Error3=", rsp3.error)
    assert str(rsp3.error) == errors.ERROR_INVALID_EVENT
    print("Transition result=", rsp3.transition_result)
    assert rsp3.transition_result is None
    print("Current state3=", rsp3.state.value)
    assert rsp3.state.value == 'Closed'

    # Open the door again
    def mock_error(ctx):
        print(ctx.get('who'), ctx.get('what'), "an error!")
        raise Exception('A mock Error!')

    rsp4 = machine.on(evt1, lambda ctx: mock_error(ctx), {
        'who': 'FooBar',
        'what': 'throw',
    })
    print("Error4=", rsp4.error)
    assert str(rsp4.error) == 'A mock Error!'
    print("Current state4=", rsp4.state.value)
    assert rsp4.state.value == 'Opened'

    # Knock Knock again
    rsp5 = machine.on(evt2, lambda: 42)
    print("Error5=", rsp5.error)
    assert rsp5.error is None
    print("Transition result=", rsp5.transition_result)
    assert rsp5.transition_result == 42
    print("Current state5=", rsp5.state.value)
    assert rsp5.state.value == 'Closed'

    # Close FSM
    machine.close()


if __name__ == '__main__':
    pytest.main()
