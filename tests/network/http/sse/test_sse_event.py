import pytest

from pypepper.network.http.sse.event import SSEEvent, new_sse_event


def test_sse_event_creation():
    """Test SSE event creation"""
    sse_event = new_sse_event(
        data={'message': 'test'},
        event='test-event',
        id='test-id-1',
    )

    assert sse_event is not None
    assert sse_event.data == {'message': 'test'}
    assert sse_event.event == 'test-event'
    assert sse_event.id == 'test-id-1'


def test_sse_event_to_server_sent_event():
    """Test conversion to FastAPI ServerSentEvent"""
    from fastapi.sse import ServerSentEvent

    sse_event = SSEEvent(
        data={'value': 42},
        event='number',
        id='evt-1',
    )

    server_sent_event = sse_event.to_server_sent_event()

    assert isinstance(server_sent_event, ServerSentEvent)
    assert server_sent_event.data == {'value': 42}
    assert server_sent_event.event == 'number'
    assert server_sent_event.id == 'evt-1'


def test_sse_event_is_independent_from_pypepper_event():
    """SSE event API should not depend on pypepper.event."""
    assert not hasattr(SSEEvent, 'from_pypepper_event')


def test_sse_event_ping():
    """Test heartbeat event"""
    ping_event = SSEEvent.ping(comment='keep-alive')

    assert ping_event.comment == 'keep-alive'
    assert ping_event.data is None
    assert ping_event.event is None


def test_sse_event_reconnect():
    """Test reconnection configuration event"""
    reconnect_event = SSEEvent.reconnect(retry_ms=5000)

    assert reconnect_event.retry == 5000
    assert reconnect_event.data is None


def test_sse_event_raw_data():
    """Test raw data mode"""
    sse_event = SSEEvent(raw_data='<html>Hello</html>')

    assert sse_event.raw_data == '<html>Hello</html>'
    assert sse_event.data is None

    server_sent_event = sse_event.to_server_sent_event()
    assert server_sent_event.raw_data == '<html>Hello</html>'


def test_sse_event_with_all_fields():
    """Test SSE event with all fields"""
    sse_event = SSEEvent(
        data={'test': 'data'},
        event='test',
        id='evt-123',
        retry=3000,
        comment='test comment',
    )

    assert sse_event.data == {'test': 'data'}
    assert sse_event.event == 'test'
    assert sse_event.id == 'evt-123'
    assert sse_event.retry == 3000
    assert sse_event.comment == 'test comment'

    server_sent_event = sse_event.to_server_sent_event()
    assert server_sent_event.data == {'test': 'data'}
    assert server_sent_event.event == 'test'
    assert server_sent_event.id == 'evt-123'
    assert server_sent_event.retry == 3000
    assert server_sent_event.comment == 'test comment'


if __name__ == '__main__':
    pytest.main()
