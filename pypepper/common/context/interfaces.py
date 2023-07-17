from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import MutableMapping
from typing import Any


class IContext(metaclass=ABCMeta):
    """
    Context interface
    """

    index: int
    context_id: str
    context: MutableMapping[Any, Any] | None
    parent: IContext | None

    @abstractmethod
    def with_value(self, key: Any, value: Any) -> IContext:
        """
        Set context key/value
        :param key: key
        :param value: value
        :return: Context
        """
        pass

    @abstractmethod
    def trace(self, index: int) -> IContext:
        """
        Trace to the context by index.
        :param index: context index.
        :return: Context.
        """
        pass

    @abstractmethod
    def length(self) -> int:
        """
        Get the length from the context with index 0 to the current context
        :return: length
        """
        pass

    @abstractmethod
    def head(self) -> IContext:
        """
        Get context chain head
        :return: context chain head
        """
        pass
