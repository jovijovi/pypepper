import re

from pypepper.common.utils import time


def test_get_datetime():
    local = time.get_datetime()
    assert isinstance(local, str)
    assert 'T' in local
    shanghai = time.get_datetime('Asia/Shanghai')
    assert isinstance(shanghai, str)
    utc = time.get_datetime('UTC')
    assert isinstance(utc, str)
    assert '+00:00' in utc or 'Z' in utc or '+0000' in utc.replace(':', '')


def test_get_local_datetime():
    result = time.get_local_datetime()
    assert isinstance(result, str)
    assert 'T' in result


def test_get_utc_datetime():
    result = time.get_utc_datetime()
    assert isinstance(result, str)
    assert 'T' in result


def test_get_date():
    local = time.get_date()
    assert local is not None
    assert re.match(r'\d{4}-\d{2}-\d{2}', str(local))
    utc = time.get_date('UTC')
    assert utc is not None


def test_get_timezone():
    result = time.get_timezone()
    assert result is not None


def test_get_unix_timestamp():
    result = time.get_unix_timestamp()
    assert isinstance(result, (int, float))
    assert result > 0


def test_parse_unix_timestamp():
    parsed = time.parse_unix_timestamp(1466097825, 'UTC')
    assert parsed is not None
    assert '2016' in str(parsed)


def test_sleep():
    start = time.get_unix_timestamp()
    time.sleep(ms=50)
    end = time.get_unix_timestamp()
    assert end >= start
