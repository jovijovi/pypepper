import pytest

from pedro.event import event
from pedro.fsm import fsm
from pedro.fsm.fsm import Transition


def test_new_state():
    state = fsm.State('Closed')
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

    def event2_handler():
        print("Event2 transition's handler: somebody close the door")
        return "#42#"

    options = fsm.Options(
        fsm_id='test-id-1',
        initial=fsm.State('Closed'),
        transitions=[
            Transition(
                event=evt1,
                from_state=[fsm.State('Closed')],
                to_state=fsm.State('Opened'),
                handler=lambda ctx: print("Event1 transition's handler:", ctx.get('who'), ctx.get('what')),
                context={
                    'who': 'Door',
                    'what': 'opened',
                },
            ),
            Transition(
                event=evt2,
                from_state=[fsm.State('Opened')],
                to_state=fsm.State('Closed'),
                handler=lambda: event2_handler(),
                context=None,
            )
        ]
    )
    machine = fsm.new(options)

    print("Initial state=", machine.current().value)

    # Open the door
    rsp1 = machine.on(evt1, lambda: print(f'Event({evt1.data.name}) finished'))
    print("Error1=", rsp1.error)
    print("Current state1=", rsp1.state.value)

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
    print("Event handler result=", rsp2.event_handler_result)
    print("Current state2=", rsp2.state.value)

    # Knock Knock
    rsp3 = machine.on(evt3)
    print("Error3=", rsp3.error)
    print("Transition result=", rsp3.transition_result)
    print("Current state3=", rsp3.state.value)

    # Open the door again
    def mock_error(ctx):
        print(ctx.get('who'), ctx.get('what'), "an error!")
        raise Exception('A mock Error!')

    rsp4 = machine.on(evt1, lambda ctx: mock_error(ctx), {
        'who': 'FooBar',
        'what': 'throw',
    })
    print("Error4=", rsp4.error)
    print("Current state4=", rsp4.state.value)

    # Knock Knock
    rsp5 = machine.on(evt2, lambda: 42)
    print("Error5=", rsp5.error)
    print("Transition result=", rsp5.transition_result)
    print("Current state5=", rsp5.state.value)

    # Close FSM
    machine.close()


if __name__ == '__main__':
    pytest.main()
