"""Dispatcher processor registry validation."""

import pytest

from pypepper.scheduler.job import Processor, dispatcher
from tests.support.optimize import assert_valueerror_under_optimize


def test_dispatcher_rejects_empty_key_and_processor():
    with pytest.raises(ValueError, match="invalid key"):
        dispatcher._get_processor("")
    with pytest.raises(ValueError, match="invalid key"):
        dispatcher._put_processor("", Processor())
    with pytest.raises(ValueError, match="invalid processor"):
        dispatcher._put_processor("proc-empty", None)  # type: ignore[arg-type]


def test_dispatcher_put_get_roundtrip_and_none_does_not_mutate():
    proc = Processor()
    dispatcher._put_processor("proc-keep", proc)
    assert dispatcher._get_processor("proc-keep") is proc
    with pytest.raises(ValueError, match="invalid processor"):
        dispatcher._put_processor("proc-keep", None)  # type: ignore[arg-type]
    assert dispatcher._get_processor("proc-keep") is proc


def test_dispatcher_validation_survives_python_optimize():
    assert_valueerror_under_optimize(
        "from pypepper.scheduler.job import dispatcher; dispatcher._get_processor('')",
        "invalid key",
    )
    assert_valueerror_under_optimize(
        "from pypepper.scheduler.job import Processor, dispatcher; dispatcher._put_processor('k', None)",
        "invalid processor",
    )
