from http import HTTPStatus


class InternalException(Exception):
    """
    Base exception class.
    """

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
