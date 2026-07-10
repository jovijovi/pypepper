from pypepper.common import cache


def test_cache_sets_are_isolated():
    cs1 = cache.new_cache_set()
    cs2 = cache.new_cache_set()

    cs1.new('x').set('k', 1)
    cs2.clear()

    assert cs1.get('x') is not None
    assert cs1.get('x').get('k') == 1
    assert cs2.get('x') is None


def test_cache_set_clear_is_local():
    cs1 = cache.new_cache_set()
    cs2 = cache.new_cache_set()

    cs1.new('a').set('k', 'v1')
    cs2.new('a').set('k', 'v2')

    cs1.clear()
    assert cs1.get('a') is None
    assert cs2.get('a').get('k') == 'v2'


def test_cache_instances_have_independent_locks():
    c1 = cache.new_cache()
    c2 = cache.new_cache()
    assert c1._lock is not c2._lock
