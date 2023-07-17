import json

import pytest

from pypepper.common.log import log
from pypepper.logo import logo


def test_log():
    log.logo(logo)

    log.trace("TRACE without reqID")
    log.debug("DEBUG without reqID")
    log.info("INFO without reqID")
    log.warn("WARN without reqID")
    log.error("ERROR without reqID")
    log.fatal("FATAL without reqID")

    log.request_id("reqID-1").trace("This is a TRACE msg")
    log.request_id("reqID-2").debug("This is a DEBUG msg")
    log.request_id("reqID-3").info("This is a INFO msg")
    log.request_id("reqID-4").warn("This is a WARN msg")
    log.request_id("reqID-5").error("This is a ERROR msg")
    log.request_id("reqID-6").fatal("This is a FATAL msg")

    word = "world"
    log.request_id(6).info("Hello, world!")
    log.request_id(7).info("Hello, {}!", word)
    log.request_id(8).info('Hello, {}!', word)
    log.request_id(9).info("""Hello, {}!""", word)
    log.request_id(10).info("{}, {}!", "Hello", "world")

    user = {
        "Name": "Jerry",
        "Age": 1,
        "Score": [0, 2, 4],
        "Files": {"foo": 1},
    }

    log.request_id().debug(json.dumps(user, indent=4))


def test_set_log_level():
    log.trace("IT'S A TRACE LOG 1")
    log.debug("IT'S A DEBUG LOG 1")

    log.set_log_level("INFO")
    log.trace("IT'S A TRACE LOG 2")
    log.debug("IT'S A DEBUG LOG 2")
    log.info("IT'S A INFO LOG 2")


if __name__ == '__main__':
    pytest.main()
