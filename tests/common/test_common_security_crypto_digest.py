import pytest

from pypepper.common.security.crypto import digest

message = '1234567890'
mock_hash_string = 'c775e7b757ede630cd0aa1113bd102661ab38829ca52a6422ab782862f268646'


def test_get():
    result = digest.get(bytes(message, 'UTF-8'), 'sha256')
    print("Hash(bytes)=", result)


def test_get_hex_str():
    result = digest.get_hex_str(message, 'sha256')
    print("Hash(hex)=", result)
    assert result == mock_hash_string


if __name__ == '__main__':
    pytest.main()
