from http import HTTPStatus


class InternalException(Exception):
    """
    Base exception class for PedroPy.
    """

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
