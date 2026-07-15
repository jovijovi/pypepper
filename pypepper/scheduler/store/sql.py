"""SQLAlchemy JobStore for MySQL and PostgreSQL."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from pypepper.helper.db import mysql, postgres
from pypepper.scheduler.store.interfaces import IJobStore, JobRecord

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
        uri = f"postgresql+psycopg://{cfg.username}:{cfg.password}@{cfg.host}:{cfg.port}/{cfg.db}"
        if cfg.sslmode:
            uri = f"{uri}?sslmode={cfg.sslmode}"
        return create_engine(uri)

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
    uri = (
        f"mysql+pymysql://{mysql_cfg.username}:{mysql_cfg.password}"
        f"@{mysql_cfg.host}:{mysql_cfg.port}/{mysql_cfg.db}?charset={mysql_cfg.charset}"
    )
    return create_engine(uri)


def _row_to_record(row: Any) -> JobRecord:
    return JobRecord(
        id=row.id,
        category=row.category,
        channel_id=row.channel_id,
        status=row.status,
        created=row.created,
        updated=row.updated,
        workflow_count=int(row.workflow_count or 0),
        version=int(row.version or 1),
    )


class SqlJobStore(IJobStore):
    """Upsert job snapshots into ``scheduler_jobs`` (MySQL or PostgreSQL)."""

    def __init__(self, backend: Literal["postgres", "mysql"], **kwargs: Any) -> None:
        self._backend = backend
        self._engine = _engine_from_config(backend, **kwargs)
        _metadata.create_all(self._engine)

    def put(self, record: JobRecord) -> None:
        values = {
            "id": record.id,
            "category": record.category,
            "channel_id": record.channel_id,
            "status": record.status,
            "created": record.created,
            "updated": record.updated,
            "workflow_count": record.workflow_count,
            "version": record.version,
        }
        update_values = {
            "category": record.category,
            "channel_id": record.channel_id,
            "status": record.status,
            "created": record.created,
            "updated": record.updated,
            "workflow_count": record.workflow_count,
            "version": record.version,
        }
        with self._engine.begin() as conn:
            if self._backend == "postgres":
                pg_stmt = pg_insert(scheduler_jobs).values(**values)
                pg_stmt = pg_stmt.on_conflict_do_update(index_elements=["id"], set_=update_values)
                conn.execute(pg_stmt)
                return
            mysql_stmt = mysql_insert(scheduler_jobs).values(**values)
            mysql_stmt = mysql_stmt.on_duplicate_key_update(**update_values)
            conn.execute(mysql_stmt)

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
