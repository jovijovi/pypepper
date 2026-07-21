"""Thread-safe TTL cache set."""

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

    def __init__(
        self,
        maxsize: int = default_cache_maxsize,
        ttl: float = default_cache_ttl,
    ):
        super().__init__(maxsize, ttl)
        self._lock = Lock()

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

    def get(self, key: Any, default: Any = None) -> Any | None:
        """
        Get value
        :param key: cache key
        :param default: default value when missing
        :return: cache value
        """

        with self._lock:
            try:
                return self[key] if key else default
            except KeyError:
                return default


class CacheSet:
    """
    A thread safe TTL cache-set
    """

    def __init__(self):
        self._lock = Lock()
        self._cache_store: MutableMapping[str, Cache] = {}

    def new(
        self,
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

        with self._lock:
            existing = self._cache_store.get(name)
            if existing is None:
                existing = Cache(maxsize, ttl)
                self._cache_store[name] = existing
            return existing

    def get(self, name: str) -> Cache | None:
        """
        Get the cache from cache-set
        :param name: cache name
        :return: cache
        """

        with self._lock:
            return self._cache_store.get(name)

    def clear(self):
        """
        Clear cache-set
        :return: None
        """

        with self._lock:
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
