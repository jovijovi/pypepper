import asyncio

import pytest

from pypepper.exceptions import InternalException
from pypepper.network.http.sse.connection import SSEConnection, SSEConnectionManager
from pypepper.network.http.sse.event import SSEEvent


@pytest.mark.asyncio
async def test_connection_creation():
    """Test connection creation"""
    manager = SSEConnectionManager()

    connection = await manager.connect(
        connection_id='test-conn-1',
        last_event_id='evt-100',
        client_ip='127.0.0.1',
        api_key='test-key',
    )

    assert connection is not None
    assert connection.connection_id == 'test-conn-1'
    assert connection.last_event_id == 'evt-100'
    assert not connection.is_closed()
    assert connection.context.context.get('client_ip') == '127.0.0.1'
    assert connection.context.context.get('api_key') == 'test-key'

    # Cleanup
    await manager.disconnect('test-conn-1')


@pytest.mark.asyncio
async def test_connection_auto_id():
    """Test auto-generated connection ID"""
    manager = SSEConnectionManager()

    connection = await manager.connect()

    assert connection is not None
    assert connection.connection_id is not None
    assert len(connection.connection_id) > 0

    # Cleanup
    await manager.disconnect(connection.connection_id)


@pytest.mark.asyncio
async def test_connection_send_event():
    """Test sending event"""
    manager = SSEConnectionManager()
    connection = await manager.connect(connection_id='test-conn-2')

    # Send event
    event = SSEEvent(data={'test': 'value'}, event='test', id='evt-1')
    success = await connection.send(event)

    assert success is True

    # Read from queue
    received_event = await asyncio.wait_for(connection._queue.get(), timeout=1.0)
    assert received_event.data == {'test': 'value'}
    assert received_event.event == 'test'

    # Cleanup
    await manager.disconnect('test-conn-2')


@pytest.mark.asyncio
async def test_connection_ping():
    """Test heartbeat"""
    manager = SSEConnectionManager()
    connection = await manager.connect(connection_id='test-conn-3')

    await connection.ping()

    # Read heartbeat from queue
    ping_event = await asyncio.wait_for(connection._queue.get(), timeout=1.0)
    assert ping_event.comment == 'heartbeat'

    # Cleanup
    await manager.disconnect('test-conn-3')


@pytest.mark.asyncio
async def test_connection_disconnect():
    """Test disconnection"""
    manager = SSEConnectionManager()
    connection = await manager.connect(connection_id='test-conn-4')

    assert not connection.is_closed()

    await manager.disconnect('test-conn-4')

    assert connection.is_closed()
    assert manager.get_connection('test-conn-4') is None


@pytest.mark.asyncio
async def test_connection_manager_broadcast():
    """Test broadcast to all connections"""
    manager = SSEConnectionManager()

    # Create multiple connections
    conn1 = await manager.connect(connection_id='test-conn-5')
    conn2 = await manager.connect(connection_id='test-conn-6')
    conn3 = await manager.connect(connection_id='test-conn-7')

    # Broadcast event
    broadcast_event = SSEEvent(
        data={'broadcast': 'message'},
        event='broadcast',
        id='bcast-1',
    )
    count = await manager.broadcast(broadcast_event)

    assert count == 3

    # Verify all connections received the event
    evt1 = await asyncio.wait_for(conn1._queue.get(), timeout=1.0)
    evt2 = await asyncio.wait_for(conn2._queue.get(), timeout=1.0)
    evt3 = await asyncio.wait_for(conn3._queue.get(), timeout=1.0)

    assert evt1.data == {'broadcast': 'message'}
    assert evt2.data == {'broadcast': 'message'}
    assert evt3.data == {'broadcast': 'message'}

    # Cleanup
    await manager.disconnect('test-conn-5')
    await manager.disconnect('test-conn-6')
    await manager.disconnect('test-conn-7')


@pytest.mark.asyncio
async def test_connection_manager_get_all():
    """Test getting all connections"""
    manager = SSEConnectionManager()

    initial_count = len(manager.get_all_connections())

    conn1 = await manager.connect(connection_id='test-conn-8')
    conn2 = await manager.connect(connection_id='test-conn-9')

    all_connections = manager.get_all_connections()
    assert len(all_connections) == initial_count + 2

    # Cleanup
    await manager.disconnect('test-conn-8')
    await manager.disconnect('test-conn-9')


@pytest.mark.asyncio
async def test_connection_queue_full():
    """Test queue full handling"""
    manager = SSEConnectionManager()
    connection = await manager.connect(connection_id='test-conn-10')

    # Fill queue to capacity
    for i in range(SSEConnection.MAX_QUEUE_SIZE):
        event = SSEEvent(data={'index': i}, event='fill', id=f'evt-{i}')
        success = await connection.send(event)
        assert success is True

    # Try to send one more (should be dropped)
    overflow_event = SSEEvent(data={'overflow': True}, event='overflow')
    success = await connection.send(overflow_event)
    assert success is False

    # Check stats
    stats = connection.get_stats()
    assert stats['dropped_events'] == 1

    # Cleanup
    await manager.disconnect('test-conn-10')


@pytest.mark.asyncio
async def test_connection_limit():
    """Test connection limit enforcement"""
    manager = SSEConnectionManager()

    # Store original limit
    original_limit = manager.MAX_CONNECTIONS

    # Clean up any existing connections first
    existing_connections = list(manager._connections.keys())
    for conn_id in existing_connections:
        await manager.disconnect(conn_id)

    try:
        # Set low limit for testing
        manager.MAX_CONNECTIONS = 2

        # Create connections up to limit
        conn1 = await manager.connect(connection_id='test-limit-1')
        conn2 = await manager.connect(connection_id='test-limit-2')

        # Try to exceed limit
        with pytest.raises(InternalException) as exc_info:
            await manager.connect(connection_id='test-limit-3')

        assert 'Maximum connections reached' in str(exc_info.value)

        # Cleanup
        await manager.disconnect('test-limit-1')
        await manager.disconnect('test-limit-2')

    finally:
        # Restore original limit
        manager.MAX_CONNECTIONS = original_limit


@pytest.mark.asyncio
async def test_connection_stats():
    """Test connection statistics"""
    manager = SSEConnectionManager()
    connection = await manager.connect(connection_id='test-conn-stats')

    # Send some events
    await connection.send(SSEEvent(data={'test': 1}, id='evt-1'))
    await connection.send(SSEEvent(data={'test': 2}, id='evt-2'))

    # Get stats
    stats = connection.get_stats()

    assert stats['connection_id'] == 'test-conn-stats'
    assert stats['queue_size'] == 2
    assert stats['dropped_events'] == 0
    assert stats['is_closed'] is False

    # Cleanup
    await manager.disconnect('test-conn-stats')


if __name__ == '__main__':
    pytest.main()
