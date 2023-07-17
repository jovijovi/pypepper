import secrets

from pypepper.exceptions import InternalException

# Minimal salt size in bytes
MIN_SALT_SIZE = 16

# Default salt size
DEFAULT_SALT_SIZE = 64


def new(size: int = DEFAULT_SALT_SIZE) -> bytes:
    """
    Generates a random salt of the specified size.
    The salt should be as unique as possible. It is recommended that a salt is random and at least 16 bytes long.
    See NIST SP 800-132 for details. Ref: https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-132.pdf
    :param size: number of bytes
    :return: a random salt
    """

    if size < MIN_SALT_SIZE:
        raise InternalException("salt size at least 16 bytes long")

    return secrets.token_bytes(size)
