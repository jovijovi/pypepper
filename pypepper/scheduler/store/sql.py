"""SQLAlchemy JobStore for MySQL and PostgreSQL."""

from __future__ import annotations

import json
from typing import Any, Literal

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, and_, case, create_engine, inspect, select, text
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from pypepper.helper.db import mysql, postgres
from pypepper.helper.db.uri import build_mysql_uri, build_postgres_uri
from pypepper.scheduler.store.interfaces import IJobStore, JobRecord
from pypepper.scheduler.store.lifecycle import existing_statuses_put_may_replace

TABLE_NAME = "scheduler_jobs"

_metadata = MetaData()

scheduler_jobs = Table(
    TABLE_NAME,
    _metadata,
    Column("id", String(36), primary_key=True),
    Column("category", String(255), nullable=True),
    Column("channel_id", String(255), nullable=False),
    Column("status", String(64), nullable=False),
    Column("created", String(64), nullable=False),
    Column("updated", String(64), nullable=False),
    Column("workflow_count", Integer, nullable=False, default=0),
    Column("version", Integer, nullable=False, default=1),
    Column("payload", Text, nullable=True),
)


def _engine_from_config(backend: Literal["postgres", "mysql"], **kwargs: Any) -> Engine:
    if backend == "postgres":
        cfg = postgres.Config(
            uri=kwargs.get("uri"),
            username=kwargs.get("username"),
            password=kwargs.get("password"),
            host=kwargs.get("host"),
            port=int(kwargs.get("port") or 5432),
            db=kwargs.get("db"),
            sslmode=kwargs.get("sslmode"),
        )
        if cfg.uri:
            return create_engine(cfg.uri)
        if not (cfg.username and cfg.password and cfg.host and cfg.db):
            raise ValueError("postgres job store requires uri=... or username, password, host, and db")
        return create_engine(
            build_postgres_uri(
                username=cfg.username,
                password=cfg.password,
                host=cfg.host,
                port=cfg.port,
                db=cfg.db,
                sslmode=cfg.sslmode,
            )
        )

    mysql_cfg = mysql.Config(
        uri=kwargs.get("uri"),
        username=kwargs.get("username"),
        password=kwargs.get("password"),
        host=kwargs.get("host"),
        port=int(kwargs.get("port") or 3306),
        db=kwargs.get("db"),
        charset=kwargs.get("charset") or "utf8mb4",
    )
    if mysql_cfg.uri:
        return create_engine(mysql_cfg.uri)
    if not (mysql_cfg.username and mysql_cfg.password and mysql_cfg.host and mysql_cfg.db):
        raise ValueError("mysql job store requires uri=... or username, password, host, and db")
    return create_engine(
        build_mysql_uri(
            username=mysql_cfg.username,
            password=mysql_cfg.password,
            host=mysql_cfg.host,
            port=mysql_cfg.port,
            db=mysql_cfg.db,
            charset=mysql_cfg.charset,
        )
    )


def _dumps_payload(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload)


def _loads_payload(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    loaded = json.loads(raw)
    if isinstance(loaded, dict):
        return loaded
    return None


def _row_to_record(row: Any) -> JobRecord:
    payload_raw = getattr(row, "payload", None)
    return JobRecord(
        id=row.id,
        category=row.category,
        channel_id=row.channel_id,
        status=row.status,
        created=row.created,
        updated=row.updated,
        workflow_count=int(row.workflow_count or 0),
        version=int(row.version or 1),
        payload=_loads_payload(payload_raw),
    )


def _ensure_schema(engine: Engine) -> None:
    _metadata.create_all(engine)
    inspector = inspect(engine)
    if TABLE_NAME not in inspector.get_table_names():
        return
    names = {c["name"] for c in inspector.get_columns(TABLE_NAME)}
    if "payload" in names:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {TABLE_NAME} ADD COLUMN payload TEXT"))


class SqlJobStore(IJobStore):
    """Upsert job snapshots into ``scheduler_jobs`` (MySQL or PostgreSQL)."""

    def __init__(self, backend: Literal["postgres", "mysql"], **kwargs: Any) -> None:
        self._backend = backend
        self._engine = _engine_from_config(backend, **kwargs)
        _ensure_schema(self._engine)

    def put(self, record: JobRecord) -> bool:
        payload_json = _dumps_payload(record.payload)
        values = {
            "id": record.id,
            "category": record.category,
            "channel_id": record.channel_id,
            "status": record.status,
            "created": record.created,
            "updated": record.updated,
            "workflow_count": record.workflow_count,
            "version": record.version,
            "payload": payload_json,
        }
        allowed = list(existing_statuses_put_may_replace(record.status))
        may_replace = and_(
            scheduler_jobs.c.status.in_(allowed),
            scheduler_jobs.c.version == record.version,
        )
        next_version = record.version + 1
        update_values = {
            "category": record.category,
            "channel_id": record.channel_id,
            "status": record.status,
            "updated": record.updated,
            "workflow_count": record.workflow_count,
            "version": next_version,
            "payload": payload_json,
        }
        with self._engine.begin() as conn:
            if self._backend == "postgres":
                pg_stmt = pg_insert(scheduler_jobs).values(**values)
                pg_stmt = pg_stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_=update_values,
                    where=may_replace,
                )
                result = conn.execute(pg_stmt)
                return bool(result.rowcount)
            mysql_stmt = mysql_insert(scheduler_jobs).values(**values)

            def _gated(new_value: object, column: Column[Any]) -> object:
                return case((may_replace, new_value), else_=column)

            mysql_stmt = mysql_stmt.on_duplicate_key_update(
                category=_gated(record.category, scheduler_jobs.c.category),
                channel_id=_gated(record.channel_id, scheduler_jobs.c.channel_id),
                status=_gated(record.status, scheduler_jobs.c.status),
                updated=_gated(record.updated, scheduler_jobs.c.updated),
                workflow_count=_gated(record.workflow_count, scheduler_jobs.c.workflow_count),
                version=_gated(next_version, scheduler_jobs.c.version),
                payload=_gated(payload_json, scheduler_jobs.c.payload),
            )
            result = conn.execute(mysql_stmt)
            return bool(result.rowcount)

    def get(self, job_id: str) -> JobRecord | None:
        with self._engine.connect() as conn:
            row = conn.execute(select(scheduler_jobs).where(scheduler_jobs.c.id == job_id)).first()
        if row is None:
            return None
        return _row_to_record(row)

    def delete(self, job_id: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(scheduler_jobs.delete().where(scheduler_jobs.c.id == job_id))

    def list(self, channel_id: str | None = None) -> list[JobRecord]:
        stmt = select(scheduler_jobs)
        if channel_id is not None:
            stmt = stmt.where(scheduler_jobs.c.channel_id == channel_id)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
        return [_row_to_record(row) for row in rows]

    def clear(self) -> None:
        with self._engine.begin() as conn:
            conn.execute(scheduler_jobs.delete())
