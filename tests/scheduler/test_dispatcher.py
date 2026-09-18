"""Dispatcher processor registry validation."""

import pytest

from pypepper.scheduler.job import Processor, dispatcher


def test_dispatcher_rejects_empty_key_and_processor():
    with pytest.raises(ValueError, match="invalid key"):
        dispatcher._get_processor("")
    with pytest.raises(ValueError, match="invalid key"):
        dispatcher._put_processor("", Processor())
    with pytest.raises(ValueError, match="invalid processor"):
        dispatcher._put_processor("proc-empty", None)  # type: ignore[arg-type]
