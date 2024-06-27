import http
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response, JSONResponse

from pypepper.common.log import log


def build_response(code: str, data: Any, msg: str = None) -> JSONResponse:
    return JSONResponse(
        status_code=http.HTTPStatus.OK,
        content=jsonable_encoder({
            "code": code,
            "msg": msg,
            "data": data,
        }),
    )


def bad_request(code: str = "400") -> JSONResponse:
    return JSONResponse(
        status_code=http.HTTPStatus.BAD_REQUEST,
        content=jsonable_encoder({
            "code": code,
            "msg": "Bad request",
        }),
    )


def not_found(code: str = "404") -> JSONResponse:
    return JSONResponse(
        status_code=http.HTTPStatus.NOT_FOUND,
        content=jsonable_encoder({
            "code": code,
            "msg": "Not found",
        }),
    )


def error(e: Exception, code: str = None) -> JSONResponse:
    if e:
        log.error("message={}", e)

    return JSONResponse(
        status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
        content=jsonable_encoder({
            "code": code,
            "msg": str(e),
        }),
    )
