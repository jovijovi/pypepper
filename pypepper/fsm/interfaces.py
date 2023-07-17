from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import Collection, Callable, MutableMapping
from typing import Any, TypeVar, ParamSpec

from pypepper.event.interfaces import IEvent

T = TypeVar("T")
P = ParamSpec("P")


class IState(metaclass=ABCMeta):
    value: str


class ITransition(metaclass=ABCMeta):
    event: IEvent
    from_state: Collection[IState]
    to_state: IState
    handler: Callable[P, T] | None
    context: MutableMapping[Any, Any] | None


class IOptions(metaclass=ABCMeta):
    fsm_id: str
    initial: IState
    transitions: Collection[ITransition]


class ITarget(metaclass=ABCMeta):
    state: IState
    handler: Callable[P, T] | None
    context: MutableMapping[Any, Any] | None


class IResponse(metaclass=ABCMeta):
    state: IState
    error: Any | None
    event_handler_result: T | None
    transition_result: T | None


class IFSM(metaclass=ABCMeta):
    @abstractmethod
    def current(self) -> IState:
        pass

    @abstractmethod
    def on(self,
           event: IEvent,
           handler: Callable[P, T] | None,
           context: MutableMapping[Any, Any] | None,
           ) -> IResponse:
        pass

    @abstractmethod
    def close(self):
        pass
