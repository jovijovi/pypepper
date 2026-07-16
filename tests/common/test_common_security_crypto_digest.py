import pytest

from pypepper.common.security.crypto import digest

message = "1234567890"
mock_hash_string = "c775e7b757ede630cd0aa1113bd102661ab38829ca52a6422ab782862f268646"


@pytest.fixture(autouse=True)
def _reset_weak_digest_warning():
    digest.reset_weak_digest_warning()
    yield
    digest.reset_weak_digest_warning()


def test_get():
    result = digest.get(bytes(message, "UTF-8"), "sha256")
    assert isinstance(result, bytes)
    assert len(result) == 32


def test_get_hex_str():
    result = digest.get_hex_str(message, "sha256")
    assert result == mock_hash_string


def test_weak_digest_warns_once(monkeypatch):
    from pypepper.common.log import log

    warns: list[str] = []
    monkeypatch.setattr(log, "warn", lambda msg, *a, **k: warns.append(str(msg)))
    digest.reset_weak_digest_warning()
    digest.get(b"x", "md5")
    digest.get(b"y", "SHA1")
    assert len(warns) == 1
    assert "md5" in warns[0]
    assert "weak" in warns[0]


def test_weak_digest_still_returns_digest():
    result = digest.get_hex_str(b"abc", "md5")
    assert len(result) == 32
