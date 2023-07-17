import http
from typing import Any

from flask import make_response, jsonify, Response

from pypepper.common.log import log


def build_response(code: str, data: Any, msg: str = None) -> Response:
    return make_response(jsonify({
        "code": code,
        "msg": msg,
        "data": data,
    }), http.HTTPStatus.OK)


def bad_request(code: str = "400") -> Response:
    return make_response(jsonify({
        "code": code,
        "msg": "Bad request",
    }), http.HTTPStatus.BAD_REQUEST)


def not_found(code: str = "404") -> Response:
    return make_response(jsonify({
        "code": code,
        "msg": "Not found",
    }), http.HTTPStatus.NOT_FOUND)


def error(e: Exception, code: str = None) -> Response:
    if e:
        log.error("message={}", e)

    return make_response(jsonify({
        "code": code,
        "msg": str(e),
    }), http.HTTPStatus.INTERNAL_SERVER_ERROR)
