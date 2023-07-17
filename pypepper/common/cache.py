from __future__ import annotations

from collections.abc import MutableMapping
from threading import Lock
from typing import Any

from cachetools import TTLCache


class Cache(TTLCache):
    """
    Thread safe TTL cache
    """

    default_cache_maxsize = 128
    default_cache_ttl = 60

    _lock = Lock()

    def __init__(self,
                 maxsize: int = default_cache_maxsize,
                 ttl: float = default_cache_ttl,
                 ):
        super().__init__(maxsize, ttl)

    def set(self, key: Any, value: Any) -> None:
        """
        Set key/value
        :param key: cache key
        :param value: cache value
        :return: None
        """

        with self._lock:
            try:
                self[key] = value
            except ValueError:
                return None

    def get(self, key: Any) -> Any | None:
        """
        Get value
        :param key: cache key
        :return: cache value
        """

        with self._lock:
            try:
                return self[key] if key else None
            except KeyError:
                return None


class CacheSet:
    """
    A thread safe TTL cache-set
    """

    _cache_store: MutableMapping[str, Cache] = {}

    def new(self,
            name: str,
            maxsize: int = Cache.default_cache_maxsize,
            ttl: float = Cache.default_cache_ttl,
            ) -> Cache:
        """
        New a cache in cache-set
        :param name: cache name
        :param maxsize: the maximum size of the cache.
        :param ttl: cache time-to-live.
        :return: cache
        """

        if not self._cache_store.get(name):
            self._cache_store[name] = Cache(maxsize, ttl)

        return self._cache_store[name]

    def get(self, name: str) -> Cache | None:
        """
        Get the cache from cache-set
        :param name: cache name
        :return: cache
        """

        return self._cache_store.get(name)

    def clear(self):
        """
        Clear cache-set
        :return: None
        """

        for name in self._cache_store:
            self._cache_store[name].clear()

        self._cache_store.clear()


def new_cache() -> Cache:
    """
    New cache
    :return: cache
    """

    return Cache()


def new_cache_set() -> CacheSet:
    """
    New cache-set.
    :return: cache-set.
    """

    return CacheSet()
