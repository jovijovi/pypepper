from __future__ import annotations

import base64
import json
from datetime import datetime

from pypepper.common.security.crypto import digest
from pypepper.common.security.crypto.elliptic.ecdsa import ecdsa
from pypepper.common.utils import time, uuid
from pypepper.event.interfaces import IData, IEvent, IHeader, IPayload


class Header(IHeader):
    default_version = "1"

    def __init__(self):
        self.namespace = ""
        self.request_id = ""
        self.sender = ""
        self.id = uuid.new_uuid()
        self.timestamp = time.get_utc_datetime()
        self.version = self.default_version


class Payload(IPayload):
    def __init__(self, dict_: dict | None = None):
        self.id = ""
        self.category = ""
        self.digest = None
        self.raw = None
        if dict_:
            for key in dict_:
                setattr(self, key, dict_[key])


class Data(IData):
    def __init__(self):
        self.flow = ""
        self.name = ""
        self.src = ""
        self.header = Header()
        self.payload = Payload()


def _data_to_dict(data: IData) -> dict:
    header = data.header
    payload = data.payload
    return {
        "flow": data.flow,
        "name": data.name,
        "src": data.src,
        "header": {
            "id": header.id,
            "namespace": header.namespace,
            "timestamp": header.timestamp.isoformat()
            if isinstance(header.timestamp, datetime)
            else str(header.timestamp),
            "version": header.version,
            "request_id": header.request_id,
            "sender": header.sender,
        },
        "payload": {
            "id": payload.id,
            "category": payload.category,
            "digest": base64.b64encode(payload.digest).decode("ascii")
            if isinstance(payload.digest, (bytes, bytearray))
            else payload.digest,
            "raw": base64.b64encode(payload.raw).decode("ascii")
            if isinstance(payload.raw, (bytes, bytearray))
            else payload.raw,
        },
    }


class Event(IEvent):
    def __init__(self, data: IData | None = None, sig: bytes | None = None):
        if not data:
            self.data = Data()
        else:
            self.data = data
        self.signature = sig

    def set_event_id(self, event_id: str):
        self.data.header.id = event_id

    def set_event_namespace(self, namespace: str):
        self.data.header.namespace = namespace

    def set_event_version(self, version: str):
        self.data.header.version = version

    def set_request_id(self, req_id: str):
        self.data.header.request_id = req_id

    def set_sender(self, sender: str):
        self.data.header.sender = sender

    def set_flow(self, flow: str):
        self.data.flow = flow

    def set_name(self, name: str):
        self.data.name = name

    def set_src(self, src: str):
        self.data.src = src

    def set_payload(self, payload: IPayload):
        self.data.payload = payload

    def add_payload(self, payload_id: str, category: str, raw: bytes, hash_alg: str | None = None) -> None:
        assert payload_id, "payload ID is empty"
        assert category, "category is empty"
        assert raw, "payload raw is empty"

        self.data.payload.id = payload_id
        self.data.payload.category = category
        self.data.payload.raw = raw

        if hash_alg:
            self.data.payload.digest = digest.get(raw, hash_alg)

    def _canonical_bytes(self) -> bytes:
        """Stable JSON encoding used for signing and marshaling."""
        payload = _data_to_dict(self.data)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def sign(self, certificate: bytes, hash_alg: str, passphrase: bytes | None = None) -> bytes:
        sig = ecdsa.sign(self._canonical_bytes(), certificate, hash_alg, passphrase)
        self.signature = sig
        return sig

    def verify(self, certificate: bytes, hash_alg: str) -> bool:
        if self.signature is None:
            return False
        return ecdsa.verify(self._canonical_bytes(), certificate, self.signature, hash_alg)

    def marshal(self) -> str:
        body = _data_to_dict(self.data)
        envelope = {
            "data": body,
            "signature": base64.b64encode(self.signature).decode("ascii") if self.signature else None,
        }
        return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def new(name: str | None = None, src: str | None = None) -> Event:
    evt = Event()
    if name is not None:
        evt.set_name(name)
    if src is not None:
        evt.set_src(src)
    return evt
