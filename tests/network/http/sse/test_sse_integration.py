import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from pypepper.network.http.sse.handlers import EchoSSEHandler, CounterSSEHandler
from pypepper.network.http.sse.stream import sse_stream


@pytest.fixture
def app():
    """Create test FastAPI application"""
    app = FastAPI()

    @app.get('/sse/echo')
    async def sse_echo_endpoint(request: Request):
        from fastapi.sse import EventSourceResponse

        handler = EchoSSEHandler(messages=['Hello', 'World'], interval=0.1)
        return EventSourceResponse(sse_stream(request, handler))

    @app.get('/sse/counter')
    async def sse_counter_endpoint(request: Request):
        from fastapi.sse import EventSourceResponse

        handler = CounterSSEHandler(start=0, end=5, interval=0.1)
        return EventSourceResponse(sse_stream(request, handler))

    return app


def test_sse_echo_endpoint(app):
    """Test SSE echo endpoint"""
    client = TestClient(app)

    with client.stream('GET', '/sse/echo') as response:
        assert response.status_code == 200
        assert 'text/event-stream' in response.headers['content-type']

        # Read some events
        events = []
        for line in response.iter_lines():
            if line:
                events.append(line)
            # Read enough lines to get connect + first echo event
            if len(events) >= 10:
                break

        assert len(events) > 0
        # Verify we got some data
        data_lines = [line for line in events if line.startswith('data:')]
        assert len(data_lines) > 0


def test_sse_counter_endpoint(app):
    """Test SSE counter endpoint"""
    client = TestClient(app)

    with client.stream('GET', '/sse/counter') as response:
        assert response.status_code == 200
        assert 'text/event-stream' in response.headers['content-type']

        # Read events
        events = []
        for line in response.iter_lines():
            if line:
                events.append(line)
            # Read enough lines
            if len(events) >= 15:
                break

        assert len(events) > 0


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
