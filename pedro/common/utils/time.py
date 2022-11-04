import arrow

ISO8601_WITH_TZ_OFFSET = 'YYYY-MM-DDTHH:mm:ss.SSSZZ'


def get_local_datetime() -> str:
    """
    Return local datetime
    :return: local datetime
    """
    return arrow.now().format(ISO8601_WITH_TZ_OFFSET)


def get_utc_datetime() -> str:
    """
    Return UTC datetime
    :return: UTC datetime
    """
    return arrow.utcnow().format(ISO8601_WITH_TZ_OFFSET)
