import time
from typing import Union

import arrow

# ISO 8601 is an international standard covering the worldwide exchange and communication of date and time-related data.
# ref: https://en.wikipedia.org/wiki/ISO_8601
ISO8601_WITH_TZ_OFFSET = 'YYYY-MM-DDTHH:mm:ss.SSSZZ'

# Time units
TIME_MS = 0.001
TIME_SECOND = TIME_MS * 1000
TIME_MINUTE = TIME_SECOND * 60
TIME_HOUR = TIME_MINUTE * 60
TIME_DAY = TIME_HOUR * 24


def get_datetime(tz: str = None) -> str:
    """
    Return datetime by timezone
    :param tz: timezone (optional)
    :return: datetime
    """

    return arrow.now(tz).format(ISO8601_WITH_TZ_OFFSET)


def get_local_datetime() -> str:
    """
    Return local datetime.
    :return: local datetime.
    """

    return get_datetime()


def get_utc_datetime() -> str:
    """
    Return UTC datetime
    :return: UTC datetime
    """

    return arrow.utcnow().format(ISO8601_WITH_TZ_OFFSET)


def get_date(tz: str = None) -> str:
    """
    Return date by timezone
    :param tz: timezone (optional)
    :return: date
    """

    return str(arrow.now(tz).date())


def get_timezone() -> str:
    """
    Return local timezone name
    :return: local timezone name
    """

    return arrow.now().timetz().tzname()


def get_unix_timestamp() -> int:
    """
    Return UNIX timestamp
    :return: UNIX timestamp
    """

    return arrow.utcnow().int_timestamp


def parse_unix_timestamp(
        timestamp: Union[int, float, str],
        tz: str = None,
) -> str:
    """
    Parse unix timestamp to datetime
    :param timestamp: UNIX timestamp
    :param tz: timezone (optional)
    :return: datetime
    """

    return arrow.arrow.Arrow.fromtimestamp(timestamp, tz).format(ISO8601_WITH_TZ_OFFSET)


def sleep(ms: int = 0, second: int = 0, minute: int = 0, hour: int = 0, day: int = 0):
    """
    Delay execution for a given number of ms/seconds/minutes/hours/days
    :param ms: Millisecond
    :param second: Second
    :param minute: Minute
    :param hour: Hour
    :param day: Day
    """

    time.sleep(TIME_MS * ms + TIME_SECOND * second + TIME_MINUTE * minute + TIME_HOUR * hour + TIME_DAY * day)
