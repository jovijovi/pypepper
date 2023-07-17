from pypepper.event import event
from pypepper.event.event import Event
from pypepper.fsm import fsm
from pypepper.scheduler.status import Status

INIT = event.new(name='init', src=Status.UNKNOWN)
SCHEDULE = event.new(name='schedule', src=Status.INITIALIZING)
RUN = event.new(name='run', src=Status.SCHEDULED)
FAIL = event.new(name='fail', src=Status.IN_PROGRESS)
COMPLETE = event.new(name='complete', src=Status.IN_PROGRESS)
CANCEL = event.new(name='cancel', src=Status.IN_PROGRESS)


class FSM:
    _options = fsm.Options(
        fsm_id='scheduler_fsm',
        initial=fsm.State(Status.UNKNOWN),
        transitions=[
            fsm.Transition(
                event=INIT,
                from_state=[fsm.State(Status.UNKNOWN)],
                to_state=fsm.State(Status.INITIALIZING),
            ),
            fsm.Transition(
                event=SCHEDULE,
                from_state=[fsm.State(Status.INITIALIZING)],
                to_state=fsm.State(Status.SCHEDULED),
            ),
            fsm.Transition(
                event=RUN,
                from_state=[fsm.State(Status.SCHEDULED)],
                to_state=fsm.State(Status.IN_PROGRESS),
            ),
            fsm.Transition(
                event=FAIL,
                from_state=[fsm.State(Status.IN_PROGRESS)],
                to_state=fsm.State(Status.FAILED),
            ),
            fsm.Transition(
                event=COMPLETE,
                from_state=[fsm.State(Status.IN_PROGRESS)],
                to_state=fsm.State(Status.COMPLETED),
            ),
            fsm.Transition(
                event=CANCEL,
                from_state=[fsm.State(Status.IN_PROGRESS)],
                to_state=fsm.State(Status.CANCELLED),
            ),
        ]
    )

    _machine = fsm.new(_options)

    def on(self, evt: Event):
        return self._machine.on(evt)
