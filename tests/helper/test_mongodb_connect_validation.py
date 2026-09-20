"""Unit tests for helper MongoDB connect validation (no running server required)."""

import pytest
from pypepper.helper.db import mongodb


def test_mongodb_connect_requires_uri_or_discrete_fields():
    with pytest.raises(ValueError, match="uri=... or username, password, host, and db"):
        mongodb.connect(mongodb.Config(host="localhost"))


def test_mongodb_connect_rejects_empty_config():
    with pytest.raises(ValueError, match="invalid database config"):
        mongodb.connect(None)  # type: ignore[arg-type]
