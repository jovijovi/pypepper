"""Hash digest helpers (bytes and hex)."""

from __future__ import annotations

import hashlib
from threading import Lock

from pypepper.common.log import log

BinaryLike = str | bytes | bytearray | memoryview

_WEAK_DIGEST_ALGS = frozenset({"md5", "sha1"})
_weak_digest_warned = False
_weak_digest_warn_lock = Lock()


def _warn_weak_digest_once(alg: str) -> None:
    """Log once that md5/sha1 digests are discouraged for new code."""
    global _weak_digest_warned
    with _weak_digest_warn_lock:
        if _weak_digest_warned:
            return
        _weak_digest_warned = True
    log.warn(
        f"digest algorithm {alg!r} is weak (md5/sha1); prefer sha256+ for new code "
        "(may be rejected in a future major release)"
    )


def reset_weak_digest_warning() -> None:
    """Reset the one-shot weak-digest warning (tests)."""
    global _weak_digest_warned
    with _weak_digest_warn_lock:
        _weak_digest_warned = False


def get(data: BinaryLike, alg: str) -> bytes:
    """
    Get hash (bytes)
    :param data: data in BinaryLike style
    :param alg: algorithm
    :return: hash (bytes)
    """

    name = alg.lower()
    if name in _WEAK_DIGEST_ALGS:
        _warn_weak_digest_once(name)

    h = hashlib.new(alg)

    if isinstance(data, str):
        h.update(bytes(data, "UTF-8"))
    else:
        h.update(data)

    return h.digest()


def get_hex_str(data: BinaryLike, alg: str) -> str:
    """
    Get hash string (hex)
    :param data: data in BinaryLike style
    :param alg: algorithm
    :return: hash string (hex)
    """

    return get(data, alg).hex()
