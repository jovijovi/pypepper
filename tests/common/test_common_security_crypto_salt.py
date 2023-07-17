import binascii

import pytest

from pypepper.common.security.crypto import salt


def test_salt():
    salt1 = salt.new()
    print("salt1=", salt1)

    salt1_hex1 = binascii.hexlify(salt1).decode('ascii')
    print("salt1_hex1=", salt1_hex1)

    salt1_hex2 = salt1.hex()
    print("salt1_hex2=", salt1_hex2)

    assert salt1_hex1 == salt1_hex2

    salt2 = salt.new(32)
    print("salt2=", salt2)
    print("salt2_hex=", salt2.hex())

    try:
        salt3 = salt.new(10)
        print("salt3=", salt3)
    except Exception as e:
        print("Except error=", e)


if __name__ == '__main__':
    pytest.main()
