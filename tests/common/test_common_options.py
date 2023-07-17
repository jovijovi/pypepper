from collections.abc import Callable
from typing import TypeVar, Any, Generic

import pytest

from pypepper.common import options
from pypepper.common.context import context
from pypepper.common.options import IOptions

T = TypeVar("T", bound=IOptions)


class MyOptions(IOptions, Generic[T]):
    name: str
    score: int = 0


F = TypeVar('F', bound=Callable[..., Any])


def with_name(name: str) -> F:
    def f(opts: MyOptions):
        opts.name = name

    return f


def with_score(score: int) -> F:
    def f(opts: MyOptions):
        opts.score = score

    return f


def test_new_options():
    opts = options.new()
    print("Options.dryrun=", opts.dryrun)
    print("Options.context=", opts.context)


def test_new_custom_options():
    opts = options.new((
        options.with_context(context.new().with_value('key1', 'value1')),
        options.with_dryrun(True),
        with_name('foo'),
        with_score(42),
    ))

    print("Options.context=", opts.context.context.get('key1'))
    print("Options.dryrun=", opts.dryrun)
    print("Options.name=", opts.name)
    print("Options.score=", opts.score)

    assert opts.context.context.get('key1') == 'value1'
    assert opts.dryrun is True
    assert opts.name == 'foo'
    assert opts.score == 42


if __name__ == '__main__':
    pytest.main()
