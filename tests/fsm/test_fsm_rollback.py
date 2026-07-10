from pypepper.event import event
from pypepper.fsm import fsm


def test_handler_failure_rolls_back_state():
    evt = event.new()
    evt.set_name('OpenDoor')
    evt.set_src('Closed')

    def boom():
        raise Exception('handler failed')

    machine = fsm.new(
        fsm.Options(
            fsm_id='rollback-test',
            initial=fsm.State('Closed'),
            transitions=[
                fsm.Transition(
                    event=evt,
                    from_state=[fsm.State('Closed')],
                    to_state=fsm.State('Opened'),
                    handler=boom,
                )
            ],
        )
    )

    assert machine.current().value == 'Closed'
    rsp = machine.on(evt)
    assert str(rsp.error) == 'handler failed'
    assert rsp.state.value == 'Closed'
    assert machine.current().value == 'Closed'


def test_caller_handler_failure_rolls_back_state():
    evt = event.new()
    evt.set_name('OpenDoor')
    evt.set_src('Closed')

    machine = fsm.new(
        fsm.Options(
            fsm_id='rollback-caller',
            initial=fsm.State('Closed'),
            transitions=[
                fsm.Transition(
                    event=evt,
                    from_state=[fsm.State('Closed')],
                    to_state=fsm.State('Opened'),
                )
            ],
        )
    )

    rsp = machine.on(evt, handler=lambda: (_ for _ in ()).throw(Exception('caller failed')))
    assert str(rsp.error) == 'caller failed'
    assert rsp.state.value == 'Closed'
    assert machine.current().value == 'Closed'
