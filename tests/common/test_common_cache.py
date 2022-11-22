import pytest
from cachetools import cached

from pypedro.common.utils.time import get_utc_datetime


@cached(cache={})
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)


def non_cache_fib(n):
    return n if n < 2 else non_cache_fib(n - 1) + non_cache_fib(n - 2)


_fib_n = 32
_result = 2178309


def test_cache():
    print(get_utc_datetime())
    x = fib(_fib_n)
    print(get_utc_datetime())
    print("Fib=", x)
    assert x == _result


def test_non_cache():
    print(get_utc_datetime())
    x = non_cache_fib(_fib_n)
    print(get_utc_datetime())
    print("Fib(NonCache)=", x)
    assert x == _result


if __name__ == '__main__':
    pytest.main()
