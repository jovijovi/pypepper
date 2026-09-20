import json

from pypepper.network.http import response


def test_build_response_ok_payload():
    resp = response.build_response("200", {"k": "v"}, msg="ok")
    assert resp.status_code == 200
    body = json.loads(resp.body)
    assert body == {"code": "200", "msg": "ok", "data": {"k": "v"}}


def test_build_response_optional_status_code_not_mapped_from_code():
    resp = response.build_response("500", {"k": "v"}, msg="fail", status_code=201)
    assert resp.status_code == 201
    body = json.loads(resp.body)
    assert body["code"] == "500"


def test_build_response_keeps_http_200_for_business_error_code():
    resp = response.build_response("500", None, msg="fail")
    assert resp.status_code == 200
    assert json.loads(resp.body)["code"] == "500"


def test_bad_request_and_not_found():
    bad = response.bad_request()
    assert bad.status_code == 400
    assert json.loads(bad.body)["msg"] == "Bad request"
    assert json.loads(bad.body)["code"] == "400"

    missing = response.not_found("nope")
    assert missing.status_code == 404
    body = json.loads(missing.body)
    assert body["code"] == "nope"
    assert body["msg"] == "Not found"


def test_error_includes_exception_message():
    resp = response.error(RuntimeError("explode"), code="500")
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body["code"] == "500"
    assert body["msg"] == "explode"
