"""Pluggable job persistence (memory / postgres / mysql / mongodb)."""

from __future__ import annotations

from typing import Any, Literal, cast

from pypepper.scheduler.store.interfaces import IJobStore, JobRecord
from pypepper.scheduler.store.memory import InMemoryJobStore

Backend = Literal["memory", "postgres", "mysql", "mongodb"]
_VALID_BACKENDS: frozenset[str] = frozenset({"memory", "postgres", "mysql", "mongodb"})

_job_store: IJobStore = InMemoryJobStore()


def get_job_store() -> IJobStore:
    return _job_store


# Module-level handle used by Job.save (updated via set_job_store).
job_store: IJobStore = _job_store


def _mark_job_store_applied() -> None:
    from pypepper.common.config import config as app_config

    app_config.mark_scheduler_job_store_applied()


def set_job_store(store: IJobStore) -> None:
    """Replace the process-wide job store and clear any deferred durable YAML flag."""
    global _job_store, job_store
    _job_store = store
    job_store = store
    _mark_job_store_applied()


def reset_job_store() -> None:
    """
    Reset to a fresh in-memory store (tests / process reset).

    Does **not** acknowledge a deferred durable YAML backend: if the current
    config still declares a non-memory ``jobStore``, deferred fail-fast is
    re-armed so ``Job.save`` cannot silently use memory.
    """
    global _job_store, job_store
    _job_store = InMemoryJobStore()
    job_store = _job_store
    from pypepper.common.config import config as app_config

    app_config._record_scheduler_job_store_deferred()


def configure_job_store(backend: Backend = "memory", **kwargs: Any) -> IJobStore:
    """
    Build and install a job store.

    Parameters
    ----------
    backend:
        ``memory`` | ``postgres`` | ``mysql`` | ``mongodb``
    **kwargs:
        Connection options forwarded to the backend (e.g. ``uri``, ``host``,
        ``port``, ``username``, ``password``, ``db``).
    """
    if backend == "memory":
        store: IJobStore = InMemoryJobStore()
    elif backend in ("postgres", "mysql"):
        from pypepper.scheduler.store.sql import SqlJobStore

        store = SqlJobStore(backend=backend, **kwargs)
    elif backend == "mongodb":
        from pypepper.scheduler.store.mongodb import MongoJobStore

        store = MongoJobStore(**kwargs)
    else:
        raise ValueError(f"unsupported job store backend: {backend!r}")

    set_job_store(store)
    return store


def setup_from_config(yml_config: Any | None = None) -> None:
    """Configure job store from YAML ``scheduler.jobStore`` (optional)."""
    if yml_config is None or not hasattr(yml_config, "scheduler"):
        return
    scheduler_cfg = yml_config.scheduler
    if scheduler_cfg is None or not hasattr(scheduler_cfg, "jobStore"):
        return
    store_cfg = scheduler_cfg.jobStore
    if store_cfg is None:
        return

    backend_raw = getattr(store_cfg, "backend", None) or "memory"
    if backend_raw not in _VALID_BACKENDS:
        raise ValueError(f"unsupported job store backend: {backend_raw!r}")
    backend = cast(Backend, backend_raw)
    # Avoid wiping an existing in-memory store when config still says memory.
    if backend == "memory" and isinstance(get_job_store(), InMemoryJobStore):
        _mark_job_store_applied()
        return

    kwargs: dict[str, Any] = {}
    for key in (
        "uri",
        "host",
        "port",
        "username",
        "password",
        "db",
        "sslmode",
        "charset",
        "auth_source",
    ):
        if hasattr(store_cfg, key):
            value = getattr(store_cfg, key)
            if value is not None:
                kwargs[key] = value

    configure_job_store(backend, **kwargs)


__all__ = [
    "Backend",
    "IJobStore",
    "InMemoryJobStore",
    "JobRecord",
    "configure_job_store",
    "get_job_store",
    "job_store",
    "reset_job_store",
    "set_job_store",
    "setup_from_config",
]
