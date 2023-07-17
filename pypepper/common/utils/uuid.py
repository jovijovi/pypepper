import uuid

from pypepper.exceptions import InternalException


def new_uuid() -> str:
    """
    Generate a new UUID(v4)
    :return: a new UUID(v4) string
    """

    return str(uuid.uuid4())


def new_uuid_32bits() -> str:
    """
    Generate a new UUID(v4) without "-"
    :return: a new UUID(v4) string without "-"
    """

    return uuid.uuid4().hex


def custom_uuid(length=6) -> str:
    """
    Generate a new UUID(v4) with specified length
    :param length: UUID length
    :return: a new UUID(v4) string
    """

    if length <= 0:
        raise InternalException("invalid length")

    return new_uuid_32bits()[0:length]
