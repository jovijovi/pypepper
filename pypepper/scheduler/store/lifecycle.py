"""JobRecord status fence for IJobStore.put (no lifecycle downgrade)."""

from __future__ import annotations

from pypepper.scheduler.status import Status

_NON_TERMINAL: frozenset[str] = frozenset(
    {
        Status.UNKNOWN.value,
        Status.INITIALIZING.value,
        Status.SCHEDULED.value,
        Status.IN_PROGRESS.value,
    }
)

# Incoming status may replace these existing statuses (including itself for retries).
_REPLACEABLE: dict[str, frozenset[str]] = {
    Status.UNKNOWN.value: frozenset({Status.UNKNOWN.value}),
    Status.INITIALIZING.value: frozenset({Status.UNKNOWN.value, Status.INITIALIZING.value}),
    Status.SCHEDULED.value: frozenset({Status.UNKNOWN.value, Status.INITIALIZING.value, Status.SCHEDULED.value}),
    Status.IN_PROGRESS.value: _NON_TERMINAL,
    Status.FAILED.value: _NON_TERMINAL | {Status.FAILED.value},
    Status.COMPLETED.value: _NON_TERMINAL | {Status.COMPLETED.value},
    Status.CANCELLED.value: _NON_TERMINAL | {Status.CANCELLED.value},
}


def existing_statuses_put_may_replace(incoming_status: str) -> frozenset[str]:
    """Statuses a ``put`` of ``incoming_status`` is allowed to overwrite."""
    allowed = _REPLACEABLE.get(incoming_status)
    if allowed is not None:
        return allowed
    return frozenset({incoming_status})


def put_applies(existing_status: str | None, incoming_status: str) -> bool:
    """True when there is no row, or the incoming status may replace ``existing_status``."""
    if existing_status is None:
        return True
    return existing_status in existing_statuses_put_may_replace(incoming_status)


def put_may_write(
    existing_status: str | None,
    existing_version: int | None,
    incoming_status: str,
    incoming_version: int,
) -> bool:
    """Status fence plus OCC: first insert always applies; updates need matching version."""
    if existing_status is None:
        return True
    if not put_applies(existing_status, incoming_status):
        return False
    return existing_version == incoming_version
