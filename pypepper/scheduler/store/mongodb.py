"""MongoDB / mongoengine JobStore."""

from __future__ import annotations

import contextlib
from typing import Any

from mongoengine import Document, IntField, StringField, disconnect
from mongoengine import connect as mongo_connect
from mongoengine.context_managers import switch_db

from pypepper.helper.db import mongodb as mongodb_helper
from pypepper.scheduler.store.interfaces import IJobStore, JobRecord

_DEFAULT_ALIAS = "pypepper_scheduler_jobs"


class SchedulerJobDoc(Document):
    """mongoengine document for job snapshots."""

    meta = {
        "collection": "scheduler_jobs",
        "strict": False,
        "db_alias": _DEFAULT_ALIAS,
    }

    id = StringField(primary_key=True)
    category = StringField(null=True)
    channel_id = StringField(required=True)
    status = StringField(required=True)
    created = StringField(required=True)
    updated = StringField(required=True)
    workflow_count = IntField(default=0)
    version = IntField(default=1)


def _doc_to_record(doc: SchedulerJobDoc) -> JobRecord:
    return JobRecord(
        id=str(doc.id),
        category=doc.category,
        channel_id=doc.channel_id,
        status=doc.status,
        created=doc.created,
        updated=doc.updated,
        workflow_count=int(doc.workflow_count or 0),
        version=int(doc.version or 1),
    )


class MongoJobStore(IJobStore):
    """Upsert job snapshots into MongoDB collection ``scheduler_jobs``."""

    def __init__(self, **kwargs: Any) -> None:
        cfg = mongodb_helper.Config(
            uri=kwargs.get("uri"),
            username=kwargs.get("username"),
            password=kwargs.get("password"),
            host=kwargs.get("host"),
            port=int(kwargs.get("port") or 27017),
            db=kwargs.get("db"),
            auth_source=kwargs.get("auth_source") or "admin",
            uuid_representation=kwargs.get("uuid_representation") or "standard",
        )
        self._alias = kwargs.get("alias") or _DEFAULT_ALIAS
        with contextlib.suppress(Exception):
            disconnect(alias=self._alias)
        if cfg.uri:
            mongo_connect(
                host=cfg.uri,
                alias=self._alias,
                uuidRepresentation="standard",
            )
        else:
            mongo_connect(
                username=cfg.username,
                password=cfg.password,
                host=cfg.host,
                port=cfg.port,
                db=cfg.db,
                authentication_source=cfg.auth_source,
                alias=self._alias,
                uuidRepresentation="standard",
            )

    def put(self, record: JobRecord) -> None:
        with switch_db(SchedulerJobDoc, self._alias):
            doc = SchedulerJobDoc(
                id=record.id,
                category=record.category,
                channel_id=record.channel_id,
                status=record.status,
                created=record.created,
                updated=record.updated,
                workflow_count=record.workflow_count,
                version=record.version,
            )
            doc.save()

    def get(self, job_id: str) -> JobRecord | None:
        with switch_db(SchedulerJobDoc, self._alias):
            doc = SchedulerJobDoc.objects(id=job_id).first()
            if doc is None:
                return None
            return _doc_to_record(doc)

    def delete(self, job_id: str) -> None:
        with switch_db(SchedulerJobDoc, self._alias):
            SchedulerJobDoc.objects(id=job_id).delete()

    def list(self, channel_id: str | None = None) -> list[JobRecord]:
        with switch_db(SchedulerJobDoc, self._alias):
            qs = SchedulerJobDoc.objects
            qs = qs(channel_id=channel_id) if channel_id is not None else qs()
            return [_doc_to_record(doc) for doc in qs]

    def clear(self) -> None:
        with switch_db(SchedulerJobDoc, self._alias):
            SchedulerJobDoc.objects.delete()
