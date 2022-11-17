from __future__ import annotations

import json
from collections.abc import MutableMapping, Collection
from typing import Any

from pedro.errors import ERROR_INVALID_EVENT
from pedro.event.interfaces import IEvent
from pedro.exceptions import InternalException
from pedro.fsm.interfaces import IState, IResponse, IFSM, IOptions, ITarget, ITransition


class State(IState):
    def __init__(self, v: str):
        self.value = v


class Transition(ITransition):
    def __init__(self,
                 event: IEvent,
                 from_state: Collection[IState],
                 to_state: IState,
                 handler: Any,
                 context: Any,
                 ):
        self.event = event
        self.from_state = from_state
        self.to_state = to_state
        self.handler = handler
        self.context = context


class Options(IOptions):
    def __init__(self,
                 fsm_id: str,
                 initial: IState,
                 transitions: Collection[ITransition],
                 ):
        self.fsm_id = fsm_id
        self.initial = initial
        self.transitions = transitions


class Target(ITarget):
    def __init__(self,
                 state: IState,
                 handler: Any,
                 context: Any,
                 ):
        self.state = state
        self.handler = handler
        self.context = context


class Response(IResponse):
    def __init__(self,
                 state: IState,
                 error: Any,
                 ):
        self.state = state
        self.error = error


class FSM(IFSM):
    _id: str
    _current: IState | None
    _mapper: MutableMapping[Any, ITarget] = {}
    _events: MutableMapping[Any, IEvent] = {}
    _states: MutableMapping[IState, bool] = {}

    def __init__(self, options: IOptions):
        self._id = options.fsm_id
        self._current = options.initial

        for tr in options.transitions:
            for from_state in tr.from_state:
                self._mapper[self.build_mapper_key(tr.event, from_state)] = Target(
                    state=tr.to_state,
                    handler=tr.handler,
                    context=tr.context,
                )
            self._states[tr.to_state] = True
            self._events[self.build_event_key(tr.event)] = tr.event

    @staticmethod
    def build_mapper_key(event: IEvent, from_state: IState) -> str:
        return json.dumps({
            "flow": event.data.flow,
            "name": event.data.name,
            "from_state": from_state.value,
        })

    @staticmethod
    def build_event_key(event: IEvent) -> str:
        return json.dumps({
            "flow": event.data.flow,
            "name": event.data.name,
        })

    def transition(self, event: IEvent, handler: Any | None = None, context: Any | None = None) -> Response:
        key = self.build_mapper_key(event, self._current)

        target = self._mapper.get(key)
        if not target:
            return Response(
                state=self._current,
                error=InternalException(ERROR_INVALID_EVENT),
            )

        self._current = target.state

        if target.handler:
            try:
                if context:
                    target.handler(context)
                else:
                    target.handler()
            except Exception as e:
                return Response(
                    state=self._current,
                    error=e,
                )

        if handler:
            try:
                if context:
                    handler(context)
                else:
                    handler()
            except Exception as e:
                return Response(
                    state=self._current,
                    error=e,
                )

        return Response(
            state=self._current,
            error=None,
        )

    def current(self) -> IState:
        """
        Get FSM current state
        :return: current state
        """

        return self._current

    def on(self, event: IEvent, handler: Any | None = None, context: Any | None = None) -> IResponse:
        return self.transition(event, handler, context)

    def close(self):
        """
        Close FSM (unsafe)
        :return: None
        """

        self._mapper.clear()
        self._events.clear()
        self._states.clear()
        self._current = None


def new(options: IOptions) -> FSM:
    return FSM(options)


def new_state(v: str) -> State:
    return State(
        v=v
    )
