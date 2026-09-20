"""Unit tests for job-store status fence predicates."""

from pypepper.scheduler.status import Status
from pypepper.scheduler.store.lifecycle import put_applies


def test_put_applies_insert_and_upgrade():
    assert put_applies(None, Status.SCHEDULED.value) is True
    assert put_applies(Status.SCHEDULED.value, Status.IN_PROGRESS.value) is True
    assert put_applies(Status.IN_PROGRESS.value, Status.COMPLETED.value) is True
    assert put_applies(Status.SCHEDULED.value, Status.CANCELLED.value) is True
    assert put_applies(Status.COMPLETED.value, Status.COMPLETED.value) is True


def test_put_applies_rejects_downgrade_and_other_terminals():
    assert put_applies(Status.COMPLETED.value, Status.SCHEDULED.value) is False
    assert put_applies(Status.IN_PROGRESS.value, Status.SCHEDULED.value) is False
    assert put_applies(Status.COMPLETED.value, Status.CANCELLED.value) is False
    assert put_applies(Status.FAILED.value, Status.COMPLETED.value) is False
    assert put_applies(Status.CANCELLED.value, Status.FAILED.value) is False


def test_put_applies_unknown_incoming_only_same_status():
    assert put_applies("Custom", "Custom") is True
    assert put_applies(Status.SCHEDULED.value, "Custom") is False
    assert put_applies("Custom", Status.SCHEDULED.value) is False
