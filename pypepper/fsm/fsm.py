"""Event-triggered finite state machine with rollback."""

from __future__ import annotations

import json
from collections.abc import Callable, Collection, MutableMapping
from typing import Any

from pypepper.errors import ERROR_INVALID_EVENT
from pypepper.event.interfaces import IEvent
from pypepper.exceptions import InternalException
from pypepper.fsm.interfaces import IFSM, IOptions, IResponse, IState, ITarget, ITransition


class State(IState):
    """
    Machine State
    """

    def __init__(self, value: str):
        self.value = value


class Transition(ITransition):
    """
    State Transition
    """

    def __init__(
        self,
        event: IEvent,
        from_state: Collection[IState],
        to_state: IState,
        handler: Callable[..., Any] | None = None,
        context: MutableMapping[Any, Any] | None = None,
    ):
        self.event = event
        self.from_state = from_state
        self.to_state = to_state
        self.handler = handler
        self.context = context


class Options(IOptions):
    """
    FSM Options
    """

    def __init__(
        self,
        fsm_id: str,
        initial: IState,
        transitions: Collection[ITransition],
    ):
        self.fsm_id = fsm_id
        self.initial = initial
        self.transitions = transitions


class Target(ITarget):
    """
    Target state with handler
    """

    def __init__(
        self,
        state: IState,
        handler: Callable[..., Any] | None = None,
        context: MutableMapping[Any, Any] | None = None,
    ):
        self.state = state
        self.handler = handler
        self.context = context


class Response(IResponse):
    """
    Transition response
    """

    def __init__(
        self,
        state: IState,
        error: Any,
        event_handler_result: Any | None = None,
        transition_result: Any | None = None,
    ):
        self.state = state
        self.error = error
        self.event_handler_result = event_handler_result
        self.transition_result = transition_result


class FSM(IFSM):
    """
    Finite State Machine
    """

    def __init__(self, options: IOptions):
        self._id = options.fsm_id
        self._current: IState | None = options.initial
        self._transitions: MutableMapping[str, ITarget] = {}
        self._events: MutableMapping[str, IEvent] = {}
        self._states: MutableMapping[IState, bool] = {}

        for tr in options.transitions:
            for from_state in tr.from_state:
                self._transitions[self._build_transition_key(tr.event, from_state)] = Target(
                    state=tr.to_state,
                    handler=tr.handler,
                    context=tr.context,
                )
                self._states[from_state] = True
            self._states[tr.to_state] = True
            self._events[self._build_event_key(tr.event)] = tr.event

    @staticmethod
    def _build_transition_key(event: IEvent, from_state: IState) -> str:
        """
        Build transition key
        :param event: event
        :param from_state: from some state (source state)
        :return: the transition key in JSON style
        """

        return json.dumps(
            {
                "flow": event.data.flow,
                "name": event.data.name,
                "from_state": from_state.value,
            }
        )

    @staticmethod
    def _build_event_key(event: IEvent) -> str:
        """
        Build event key
        :param event: event
        :return: the event key in JSON style
        """

        return json.dumps(
            {
                "flow": event.data.flow,
                "name": event.data.name,
            }
        )

    def _transition(
        self,
        event: IEvent,
        handler: Callable[..., Any] | None = None,
        context: MutableMapping[Any, Any] | None = None,
    ) -> Response:
        """
        Transition state
        :param event: event
        :param handler: transition handler
        :param context: transition handler's context
        :return: transition response
        """

        if self._current is None:
            raise InternalException(ERROR_INVALID_EVENT)

        key = self._build_transition_key(event, self._current)

        target = self._transitions.get(key)
        if not target:
            return Response(
                state=self._current,
                error=InternalException(ERROR_INVALID_EVENT),
            )

        prev = self._current
        self._current = target.state

        event_handler_result: Any | None = None
        if target.handler:
            try:
                event_handler_result = target.handler(target.context) if target.context else target.handler()
            except Exception as e:
                self._current = prev
                return Response(
                    state=self._current,
                    error=e,
                )

        transition_result: Any | None = None
        if handler:
            try:
                transition_result = handler(context) if context else handler()
            except Exception as e:
                self._current = prev
                return Response(
                    state=self._current,
                    error=e,
                    event_handler_result=event_handler_result,
                )

        return Response(
            state=self._current,
            error=None,
            event_handler_result=event_handler_result,
            transition_result=transition_result,
        )

    def current(self) -> IState | None:
        """
        Get FSM current state.
        :return: current state (None after close)
        """

        return self._current

    def on(
        self,
        event: IEvent,
        handler: Callable[..., Any] | None = None,
        context: MutableMapping[Any, Any] | None = None,
    ) -> IResponse:
        """
        Trigger event
        :param event: event
        :param handler: transition handler
        :param context: transition handler's context
        :return: transition response
        """

        return self._transition(event, handler, context)

    def close(self):
        """
        Close FSM (unsafe)
        :return: None
        """

        self._transitions.clear()
        self._events.clear()
        self._states.clear()
        self._current = None


def new(options: IOptions) -> FSM:
    """
    New an FSM.
    :param options: FSM options.
    :return: instance of FSM.
    """

    return FSM(options)
