from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, ParamSpec

from pypepper.common.context.interfaces import IContext
from pypepper.common.utils import uuid

T = TypeVar("T")
P = ParamSpec("P")


class Context(IContext):
    """
    Context
    """

    def __init__(self,
                 context_id: str | None = None,
                 parent: IContext | None = None,
                 ):
        self.index = 0
        self.context_id = context_id
        self.context = {}
        self.parent = parent

        if parent:
            self.index = parent.index + 1

    def with_value(self, key: Any, value: Any) -> IContext:
        """
        Set context key/value
        :param key: key
        :param value: value
        :return: Context
        """

        self.context[key] = value
        return self

    def trace(self, index: int) -> IContext:
        """
        Trace to the context by index.
        :param index: context index.
        :return: Context.
        """

        if self.index == index:
            return self

        return self.parent.trace(index)

    def length(self) -> int:
        """
        Get the length from the context with index 0 to the current context
        :return: length
        """

        return self.index + 1

    def head(self) -> IContext:
        """
        Get context chain head
        :return: context chain head
        """

        return self.trace(0)


def new(
        context_id: str | None = None,
        parent: Context | None = None,
) -> Context:
    """
    New context.
    :param context_id: new context ID (optional).
    :param parent: the parent context (optional).
    :return: context.
    """

    return Context(
        context_id=context_id,
        parent=parent,
    )


def born(
        length: int,
        parent: Context | None = None,
        id_provider: Callable[P, T] | None = None,
) -> Context:
    """
    Born the context chain.
    :param length: chain length.
    :param parent: parent context.
    :param id_provider: context ID provider.
    :return: context.
    """

    if parent:
        if parent.index == length - 1:
            return parent

        child = new(
            parent=parent,
            context_id=id_provider() if id_provider else uuid.new_uuid()
        )

        return born(
            length=length,
            parent=child,
            id_provider=id_provider
        )

    head = new(
        context_id=id_provider() if id_provider else uuid.new_uuid()
    )

    return born(
        length=length,
        parent=head,
        id_provider=id_provider,
    )
