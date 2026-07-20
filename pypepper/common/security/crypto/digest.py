"""Hash digest helpers (bytes and hex)."""

from __future__ import annotations

import hashlib

BinaryLike = str | bytes | bytearray | memoryview

_REJECTED_DIGEST_ALGS = frozenset({"md5", "sha1"})


def get(data: BinaryLike, alg: str) -> bytes:
    """
    Get hash (bytes)

    :param data: data in BinaryLike style
    :param alg: algorithm (``md5`` / ``sha1`` are rejected)
    :return: hash (bytes)
    :raises ValueError: if ``alg`` is ``md5`` or ``sha1`` (case-insensitive)
    """

    name = alg.lower()
    if name in _REJECTED_DIGEST_ALGS:
        raise ValueError(f"digest algorithm {alg!r} is not allowed; use sha256 or stronger")

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
    :param alg: algorithm (``md5`` / ``sha1`` are rejected)
    :return: hash string (hex)
    :raises ValueError: if ``alg`` is ``md5`` or ``sha1`` (case-insensitive)
    """

    return get(data, alg).hex()
