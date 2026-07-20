import pytest

from pypepper.common.security.crypto import digest

message = "1234567890"
mock_hash_string = "c775e7b757ede630cd0aa1113bd102661ab38829ca52a6422ab782862f268646"


def test_get():
    result = digest.get(bytes(message, "UTF-8"), "sha256")
    assert isinstance(result, bytes)
    assert len(result) == 32


def test_get_hex_str():
    result = digest.get_hex_str(message, "sha256")
    assert result == mock_hash_string


@pytest.mark.parametrize("alg", ["md5", "MD5", "sha1", "SHA1"])
def test_weak_digest_rejected(alg: str):
    with pytest.raises(ValueError, match="not allowed"):
        digest.get(b"x", alg)
    with pytest.raises(ValueError, match="not allowed"):
        digest.get_hex_str(b"x", alg)
