import asyncio
from types import SimpleNamespace

import pytest

from pypepper.network.http.sse.handlers import EchoSSEHandler, CounterSSEHandler
from pypepper.network.http.sse.stream import sse_stream


class _MockRequest:
    def __init__(self, disconnect_after: int = 6):
        self.headers = {}
        self.state = SimpleNamespace()
        self.client = SimpleNamespace(host='testclient')
        self._disconnect_after = disconnect_after
        self._checks = 0

    async def is_disconnected(self) -> bool:
        self._checks += 1
        return self._checks > self._disconnect_after


async def _collect_stream_chunks(handler, max_chunks: int) -> list[str]:
    request = _MockRequest(disconnect_after=max_chunks + 2)
    stream = sse_stream(request, handler)
    chunks: list[str] = []
    try:
        for _ in range(max_chunks):
            chunk = await asyncio.wait_for(anext(stream), timeout=1.0)
            chunks.append(chunk)
    finally:
        await stream.aclose()
    return chunks


@pytest.mark.asyncio
async def test_sse_echo_stream_non_blocking():
    """Echo stream should emit data quickly without blocking."""
    chunks = await _collect_stream_chunks(
        EchoSSEHandler(messages=['Hello'], interval=0.01),
        max_chunks=2,
    )

    assert any('event: connect' in chunk for chunk in chunks)
    assert any('event: echo' in chunk for chunk in chunks)
    assert any('Hello' in chunk for chunk in chunks)


@pytest.mark.asyncio
async def test_sse_counter_stream_non_blocking():
    """Counter stream should emit counter payload quickly without blocking."""
    chunks = await _collect_stream_chunks(
        CounterSSEHandler(start=0, end=1, interval=0.01),
        max_chunks=3,
    )
    assert any('event: counter' in chunk for chunk in chunks)
    assert any('"count": 0' in chunk for chunk in chunks)


@pytest.mark.asyncio
async def test_sse_handler_lifecycle():
    """Test SSE handler lifecycle"""
    from pypepper.network.http.sse.connection import connection_manager

    handler = EchoSSEHandler(messages=['Test'], interval=0.1)

    connection = await connection_manager.connect(connection_id='test-lifecycle')

    # Test on_connect
    await handler.on_connect(connection)

    # Verify connect message was sent
    import asyncio

    connect_event = await asyncio.wait_for(connection._queue.get(), timeout=1.0)
    assert connect_event.event == 'connect'
    assert connect_event.data['connection_id'] == 'test-lifecycle'

    # Test event generation
    events = []
    async for event in handler.generate_events(connection):
        events.append(event)

    assert len(events) == 1
    assert events[0].data['message'] == 'Test'

    # Test on_disconnect
    await handler.on_disconnect(connection)

    # Cleanup
    await connection_manager.disconnect('test-lifecycle')


@pytest.mark.asyncio
async def test_multiple_concurrent_connections():
    """Test multiple concurrent SSE connections"""
    from pypepper.network.http.sse.connection import connection_manager
    from pypepper.network.http.sse.event import SSEEvent

    # Create multiple connections
    connections = []
    for i in range(5):
        conn = await connection_manager.connect(connection_id=f'test-multi-{i}')
        connections.append(conn)

    # Broadcast an event
    broadcast_event = SSEEvent(
        data={'test': 'broadcast'},
        event='test',
        id='test-1',
    )
    count = await connection_manager.broadcast(broadcast_event)

    assert count == 5

    # Cleanup
    for i in range(5):
        await connection_manager.disconnect(f'test-multi-{i}')


if __name__ == '__main__':
    pytest.main()
