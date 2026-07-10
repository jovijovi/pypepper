from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Collection, MutableMapping
from typing import Any

from pypepper.event.interfaces import IEvent


class IState(metaclass=ABCMeta):
    value: str


class ITransition(metaclass=ABCMeta):
    event: IEvent
    from_state: Collection[IState]
    to_state: IState
    handler: Callable[..., Any] | None
    context: MutableMapping[Any, Any] | None


class IOptions(metaclass=ABCMeta):
    fsm_id: str
    initial: IState
    transitions: Collection[ITransition]


class ITarget(metaclass=ABCMeta):
    state: IState
    handler: Callable[..., Any] | None
    context: MutableMapping[Any, Any] | None


class IResponse(metaclass=ABCMeta):
    state: IState
    error: Any | None
    event_handler_result: Any | None
    transition_result: Any | None


class IFSM(metaclass=ABCMeta):
    @abstractmethod
    def current(self) -> IState | None:
        pass

    @abstractmethod
    def on(
        self,
        event: IEvent,
        handler: Callable[..., Any] | None = None,
        context: MutableMapping[Any, Any] | None = None,
    ) -> IResponse:
        pass

    @abstractmethod
    def close(self):
        pass
