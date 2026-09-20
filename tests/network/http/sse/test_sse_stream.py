from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from pypepper.network.http.sse.event import SSEEvent
from pypepper.network.http.sse.handlers import BaseSSEHandler
from pypepper.network.http.sse.interfaces import ISSEConnection, ISSEHandler
from pypepper.network.http.sse.stream import _serialize_sse_event, sse_stream


class _MockRequest:
    def __init__(self, disconnect_after: int = 6):
        self.headers = {}
        self.state = SimpleNamespace()
        self.client = SimpleNamespace(host="testclient")
        self._disconnect_after = disconnect_after
        self._checks = 0

    async def is_disconnected(self) -> bool:
        self._checks += 1
        return self._checks > self._disconnect_after


def test_serialize_sse_event_comment_event_id_retry_and_json():
    event = SSEEvent(
        data={"a": 1},
        event="tick",
        id="e1",
        retry=1500,
        comment="keep",
    )
    text = _serialize_sse_event(event.to_server_sent_event())
    assert text.startswith(":keep\n")
    assert "event: tick\n" in text
    assert "id: e1\n" in text
    assert "retry: 1500\n" in text
    assert 'data: {"a": 1}' in text
    assert text.endswith("\n\n")


def test_serialize_sse_event_raw_data_multiline():
    event = SSEEvent(raw_data="line1\nline2")
    text = _serialize_sse_event(event.to_server_sent_event())
    assert "data: line1\n" in text
    assert "data: line2\n" in text
    assert text.endswith("\n\n")


def test_serialize_sse_event_ping():
    text = _serialize_sse_event(SSEEvent.ping().to_server_sent_event())
    assert text == ":heartbeat\n\n"


def test_stream_timeout_seconds_defaults_when_config_fails(monkeypatch):
    def boom():
        raise RuntimeError("no-config")

    monkeypatch.setattr(
        "pypepper.network.http.sse.stream.config.get_yml_config",
        boom,
    )
    from pypepper.network.http.sse.stream import _stream_timeout_seconds

    assert _stream_timeout_seconds() == 30.0


@pytest.mark.asyncio
async def test_sse_stream_sends_heartbeat_on_timeout(monkeypatch):
    monkeypatch.setattr(
        "pypepper.network.http.sse.stream._stream_timeout_seconds",
        lambda: 0.05,
    )
    request = _MockRequest(disconnect_after=8)
    stream = sse_stream(request, BaseSSEHandler())
    chunks: list[str] = []
    try:
        for _ in range(3):
            chunks.append(await asyncio.wait_for(anext(stream), timeout=2.0))
    finally:
        await stream.aclose()
    assert any(":heartbeat" in chunk for chunk in chunks)


@pytest.mark.asyncio
async def test_sse_stream_handler_generate_error_still_disconnects(monkeypatch):
    monkeypatch.setattr(
        "pypepper.network.http.sse.stream._stream_timeout_seconds",
        lambda: 0.05,
    )
    disconnected = asyncio.Event()

    class _BoomHandler(ISSEHandler):
        async def on_connect(self, connection: ISSEConnection) -> None:
            return None

        async def on_disconnect(self, connection: ISSEConnection) -> None:
            disconnected.set()

        async def generate_events(self, connection: ISSEConnection):
            raise RuntimeError("gen-failed")
            yield  # pragma: no cover

    request = _MockRequest(disconnect_after=3)
    stream = sse_stream(request, _BoomHandler())
    try:
        async for _chunk in stream:
            pass
    finally:
        await stream.aclose()
    assert disconnected.is_set()
