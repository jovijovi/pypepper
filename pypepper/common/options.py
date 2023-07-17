from __future__ import annotations

from abc import ABCMeta
from collections.abc import Callable
from typing import TypeVar, Any

from pypepper.common.context.context import IContext
from pypepper.common.context.context import new as new_context


class IOptions(metaclass=ABCMeta):
    """
    Options interface
    """

    dryrun: bool = False
    context: IContext

    def __init__(self, context: IContext, dryrun: bool = False):
        self.context = context
        self.dryrun = dryrun


T = TypeVar("T", bound=IOptions)
F = TypeVar('F', bound=Callable[..., Any])


def new(option_funcs: tuple[F, ...] | None = ()) -> T:
    """
    New options.
    :param option_funcs: option functions.
    :return: options.
    """

    opts = IOptions(
        dryrun=False,
        context=new_context(),
    )

    for func in option_funcs:
        func(opts)

    return opts


def with_context(ctx: IContext) -> F:
    """
    With context options
    :param ctx: context
    :return: init context function
    """

    def f(opts: IOptions):
        opts.context = ctx

    return f


def with_dryrun(is_dryrun: bool) -> F:
    """
    With dryrun options
    :param is_dryrun: dryrun True/False
    :return: init dryrun function
    """

    def f(opts: IOptions):
        opts.dryrun = is_dryrun

    return f
