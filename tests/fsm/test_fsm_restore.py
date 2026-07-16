"""FSM restore API tests."""

from pypepper.event import event
from pypepper.fsm import fsm


def test_restore_sets_current_without_transition():
    evt = event.new()
    evt.set_name("Open")
    evt.set_src("Closed")

    machine = fsm.new(
        fsm.Options(
            fsm_id="restore-test",
            initial=fsm.State("Closed"),
            transitions=[
                fsm.Transition(
                    event=evt,
                    from_state=[fsm.State("Closed")],
                    to_state=fsm.State("Opened"),
                )
            ],
        )
    )

    assert machine.current().value == "Closed"
    machine.restore(fsm.State("Opened"))
    assert machine.current().value == "Opened"

    # Restored state is not a transition; Open from Opened is invalid.
    rsp = machine.on(evt)
    assert rsp.error is not None
    assert machine.current().value == "Opened"


def test_restore_none_clears_current():
    machine = fsm.new(
        fsm.Options(
            fsm_id="restore-none",
            initial=fsm.State("A"),
            transitions=[],
        )
    )
    machine.restore(None)
    assert machine.current() is None
