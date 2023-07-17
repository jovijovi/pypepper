import pytest
from cachetools import cached

from pypepper.common import cache
from pypepper.common.utils import time


@cached(cache={})
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)


def non_cache_fib(n):
    return n if n < 2 else non_cache_fib(n - 1) + non_cache_fib(n - 2)


_fib_n = 32
_result = 2178309


def test_cache_func():
    print(time.get_utc_datetime())
    x = fib(_fib_n)
    print(time.get_utc_datetime())
    print("Fib=", x)
    assert x == _result


def test_non_cache_func():
    print(time.get_utc_datetime())
    x = non_cache_fib(_fib_n)
    print(time.get_utc_datetime())
    print("Fib(NonCache)=", x)
    assert x == _result


def test_cache_set():
    # New cache-set
    cache_set = cache.new_cache_set()

    # New cache1
    cache1a = cache_set.new('cache1')
    cache1a.set('key1', 'value1')
    value1 = cache1a.get('key1')
    print(f"cache1a.key=key1, value={value1}")
    assert value1 == 'value1'

    # Get cache1
    cache1b = cache_set.get('cache1')
    print(f"cache1b.key=key1, value={cache1b.get('key1')}")
    assert cache1b.get('key1') == 'value1'

    # New cache2
    cache2 = cache_set.new(
        name='cache2',
        ttl=2,
        maxsize=4,
    )
    cache2.set('key2', 'value2')
    cache2.set('key3', 'value3')
    cache2.set('key4', 'value4')
    print("Sleeping for 1 seconds...")
    time.sleep(second=1)
    print("cache2.key2, value=", cache2.get('key2'))
    print("cache2.key3, value=", cache2.get('key3'))
    print("cache2.key4, value=", cache2.get('key4'))
    print("Sleeping for 1 seconds...")
    time.sleep(second=1)
    print("cache2.key2, value=", cache2.get('key2'))
    print("cache2.key3, value=", cache2.get('key3'))
    print("cache2.key4, value=", cache2.get('key4'))

    # Clear cache-set
    cache_set.clear()
    print(f"cache1a.key=key1, value={cache1a.get('key1')}")
    print(f"cache1b.key=key1, value={cache1b.get('key1')}")
    assert cache1a.get('key1') is None
    assert cache1b.get('key1') is None


def test_empty_cache_set():
    cache_set = cache.new_cache_set()

    none_cache_set = cache_set.get('NOT_EXISTED')
    assert none_cache_set is None

    cache1 = cache_set.new('cache1')

    nothing1 = cache1.get('foo')
    assert nothing1 is None

    nothing2 = cache1.get(None)
    assert nothing2 is None


if __name__ == '__main__':
    pytest.main()
