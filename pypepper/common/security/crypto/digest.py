import hashlib
from typing import Union

BinaryLike = Union[str, bytes, bytearray, memoryview]


def get(data: BinaryLike, alg: str) -> bytes:
    """
    Get hash (bytes)
    :param data: data in BinaryLike style
    :param alg: algorithm
    :return: hash (bytes)
    """

    h = hashlib.new(alg)

    if isinstance(data, str):
        h.update(bytes(data, 'UTF-8'))
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
