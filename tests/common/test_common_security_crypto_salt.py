import binascii

import pytest

from pypepper.common.security.crypto import salt
from pypepper.exceptions import InternalException


def test_salt():
    salt1 = salt.new()
    assert isinstance(salt1, bytes)
    assert len(salt1) == salt.DEFAULT_SALT_SIZE
    assert binascii.hexlify(salt1).decode('ascii') == salt1.hex()

    salt2 = salt.new(32)
    assert len(salt2) == 32

    with pytest.raises(InternalException, match='at least 16'):
        salt.new(10)
