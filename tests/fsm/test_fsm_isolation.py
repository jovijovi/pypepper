from pypepper.event import event
from pypepper.fsm import fsm


def _make_fsm(initial: str, event_name: str, to_state: str = 'DONE', flow: str | None = None):
    evt = event.new()
    evt.set_name(event_name)
    evt.set_src(initial)
    if flow:
        evt.set_flow(flow)

    opts = fsm.Options(
        fsm_id=f'fsm-{initial}-{event_name}',
        initial=fsm.State(initial),
        transitions=[
            fsm.Transition(
                event=evt,
                from_state=[fsm.State(initial)],
                to_state=fsm.State(to_state),
            )
        ],
    )
    return fsm.new(opts), evt


def test_two_fsms_do_not_share_transitions():
    m1, e1 = _make_fsm(initial='A', event_name='go1')
    m2, e2 = _make_fsm(initial='B', event_name='go2')

    assert m1.current().value == 'A'
    assert m2.current().value == 'B'

    rsp1 = m1.on(e1)
    assert rsp1.error is None
    assert rsp1.state.value == 'DONE'
    assert m2.current().value == 'B'

    rsp2 = m2.on(e2)
    assert rsp2.error is None
    assert rsp2.state.value == 'DONE'


def test_close_does_not_affect_other_fsm():
    m1, e1 = _make_fsm(initial='A', event_name='go1')
    m2, e2 = _make_fsm(initial='B', event_name='go2')

    m1.close()
    assert m1.current() is None

    rsp2 = m2.on(e2)
    assert rsp2.error is None
    assert rsp2.state.value == 'DONE'


def test_overlapping_transition_keys_are_per_instance():
    m1, e1 = _make_fsm(initial='S', event_name='evt', to_state='DONE', flow='f1')
    m2, e2 = _make_fsm(initial='S', event_name='evt', to_state='OTHER', flow='f1')

    assert m1.on(e1).state.value == 'DONE'
    assert m2.on(e2).state.value == 'OTHER'
