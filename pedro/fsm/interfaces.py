from abc import ABCMeta, abstractmethod
from collections.abc import Collection
from typing import Any

from pedro.event.interfaces import IEvent


class IState(metaclass=ABCMeta):
    value: str


class ITransition(metaclass=ABCMeta):
    event: IEvent
    from_state: Collection[IState]
    to_state: IState
    handler: Any  # TODO
    context: Any  # TODO


class IOptions(metaclass=ABCMeta):
    fsm_id: str
    initial: IState
    transitions: Collection[ITransition]


class ITarget(metaclass=ABCMeta):
    state: IState
    handler: Any  # TODO
    context: Any  # TODO


class IResponse(metaclass=ABCMeta):
    state: IState
    error: Any  # TODO


class IFSM(metaclass=ABCMeta):
    @abstractmethod
    def current(self) -> IState:
        pass

    @abstractmethod
    def on(self, event: IEvent, handler: Any, context: Any) -> IResponse:
        pass

    @abstractmethod
    def close(self):
        pass
