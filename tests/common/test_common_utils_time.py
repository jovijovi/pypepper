import pytest

from pypepper.common.utils import time


def test_get_datetime():
    print("Datetime(Local)=", time.get_datetime())
    print("Datetime(America/Los_Angeles)=", time.get_datetime('America/Los_Angeles'))
    print("Datetime(America/Toronto)=", time.get_datetime('America/Toronto'))
    print("Datetime(America/New_York)=", time.get_datetime('America/New_York'))
    print("Datetime(UTC)=", time.get_datetime('UTC'))
    print("Datetime(Europe/London)=", time.get_datetime('Europe/London'))
    print("Datetime(Africa/Cairo)=", time.get_datetime('Africa/Cairo'))
    print("Datetime(Europe/Moscow)=", time.get_datetime('Europe/Moscow'))
    print("Datetime(Asia/Qatar)=", time.get_datetime('Asia/Qatar'))
    print("Datetime(Asia/Dubai)=", time.get_datetime('Asia/Dubai'))
    print("Datetime(Asia/Shanghai)=", time.get_datetime('Asia/Shanghai'))
    print("Datetime(Asia/Singapore)=", time.get_datetime('Asia/Singapore'))
    print("Datetime(Asia/Tokyo)=", time.get_datetime('Asia/Tokyo'))
    print("Datetime(Australia/Sydney)=", time.get_datetime('Australia/Sydney'))


def test_get_local_datetime():
    result = time.get_local_datetime()
    print("LocalDatetime=", result)


def test_get_utc_datetime():
    result = time.get_utc_datetime()
    print("UTCDatetime=", result)


def test_get_date():
    print("Date(Local)=", time.get_date())
    print("Date(America/Los_Angeles)=", time.get_date('America/Los_Angeles'))
    print("Date(America/Toronto)=", time.get_date('America/Toronto'))
    print("Date(America/New_York)=", time.get_date('America/New_York'))
    print("Date(UTC)=", time.get_date('UTC'))
    print("Date(Europe/London)=", time.get_date('Europe/London'))
    print("Date(Africa/Cairo)=", time.get_date('Africa/Cairo'))
    print("Date(Europe/Moscow)=", time.get_date('Europe/Moscow'))
    print("Date(Asia/Qatar)=", time.get_date('Asia/Qatar'))
    print("Date(Asia/Dubai)=", time.get_date('Asia/Dubai'))
    print("Date(Asia/Shanghai)=", time.get_date('Asia/Shanghai'))
    print("Date(Asia/Singapore)=", time.get_date('Asia/Singapore'))
    print("Date(Asia/Tokyo)=", time.get_date('Asia/Tokyo'))
    print("Date(Australia/Sydney)=", time.get_date('Australia/Sydney'))


def test_get_timezone():
    result = time.get_timezone()
    print("Timezone=", result)


def test_get_unix_timestamp():
    result = time.get_unix_timestamp()
    print("UnixTimestamp=", result)


def test_parse_unix_timestamp():
    print("Date(Local)=", time.parse_unix_timestamp(1466097825))
    print("Date(America/Los_Angeles)=", time.parse_unix_timestamp(1466097825.123, 'America/Los_Angeles'))
    print("Date(America/Toronto)=", time.parse_unix_timestamp("1466097825", 'America/Toronto'))
    print("Date(America/New_York)=", time.parse_unix_timestamp(1466097825, 'America/New_York'))
    print("Date(UTC)=", time.parse_unix_timestamp(1466097825, 'UTC'))
    print("Date(Europe/London)=", time.parse_unix_timestamp(1466097825, 'Europe/London'))
    print("Date(Africa/Cairo)=", time.parse_unix_timestamp(1466097825, 'Africa/Cairo'))
    print("Date(Europe/Moscow)=", time.parse_unix_timestamp(1466097825, 'Europe/Moscow'))
    print("Date(Asia/Qatar)=", time.parse_unix_timestamp(1466097825, 'Asia/Qatar'))
    print("Date(Asia/Dubai)=", time.parse_unix_timestamp(1466097825, 'Asia/Dubai'))
    print("Date(Asia/Shanghai)=", time.parse_unix_timestamp(1466097825, 'Asia/Shanghai'))
    print("Date(Asia/Singapore)=", time.parse_unix_timestamp(1466097825, 'Asia/Singapore'))
    print("Date(Asia/Tokyo)=", time.parse_unix_timestamp(1466097825, 'Asia/Tokyo'))
    print("Date(Australia/Sydney)=", time.parse_unix_timestamp(1466097825, 'Australia/Sydney'))


def test_sleep():
    print("Test sleeping...")
    time.sleep()
    time.sleep(ms=500)
    time.sleep(second=1)
    # time.sleep(minute=1)
    # time.sleep(hour=1)
    # time.sleep(day=1)
    print("Wake up")


if __name__ == '__main__':
    pytest.main()
