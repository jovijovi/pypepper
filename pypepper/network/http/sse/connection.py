from __future__ import annotations

import asyncio
from collections.abc import MutableMapping
from threading import Lock

from pypepper.common.context import Context
from pypepper.common.log import log
from pypepper.common.utils import uuid
from pypepper.exceptions import InternalException
from pypepper.network.http.sse.interfaces import (
    ISSEConnection,
    ISSEConnectionManager,
    ISSEEvent,
)


class SSEConnection(ISSEConnection):
    """SSE Connection implementation"""

    # Queue capacity limit (per connection)
    MAX_QUEUE_SIZE = 500

    def __init__(
        self,
        connection_id: str,
        queue: asyncio.Queue,
        context: Context | None = None,
        last_event_id: str | None = None,
    ):
        self.connection_id = connection_id
        self.context = context or Context(context_id=connection_id)
        self.last_event_id = last_event_id
        self._queue = queue
        self._closed = False
        self._dropped_events = 0

    async def send(self, event: ISSEEvent) -> bool:
        """
        Send event to client

        :param event: SSE event
        :return: True if sent successfully, False if dropped
        """
        if self._closed:
            return False

        try:
            # Non-blocking mode: drop event if queue is full
            self._queue.put_nowait(event)
            log.request_id(self.connection_id).debug(
                f"SSE event sent: event={event.event}, id={event.id}"
            )
            return True

        except asyncio.QueueFull:
            self._dropped_events += 1
            log.request_id(self.connection_id).warn(
                f"SSE event dropped (queue full): event={event.event}, "
                f"total_dropped={self._dropped_events}"
            )
            return False

    async def ping(self) -> None:
        """Send heartbeat to keep connection alive"""
        from pypepper.network.http.sse.event import SSEEvent

        await self.send(SSEEvent.ping())

    async def disconnect(self) -> None:
        """Disconnect and cleanup resources"""
        self._closed = True
        log.request_id(self.connection_id).info(
            f"SSE connection closed: {self.connection_id}"
        )

    def is_closed(self) -> bool:
        """
        Check if connection is closed
        :return: True if closed
        """
        return self._closed

    def get_stats(self) -> dict:
        """
        Get connection statistics
        :return: Statistics dict
        """
        return {
            'connection_id': self.connection_id,
            'queue_size': self._queue.qsize(),
            'dropped_events': self._dropped_events,
            'is_closed': self._closed,
            'last_event_id': self.last_event_id,
        }


class SSEConnectionManager(ISSEConnectionManager):
    """SSE Connection Manager (singleton)"""

    # Connection limits (for 100 concurrent users)
    MAX_CONNECTIONS = 100
    MAX_CONNECTIONS_PER_IP = 5

    _lock = Lock()
    _connections: MutableMapping[str, SSEConnection] = {}

    def __init__(self):
        pass

    async def connect(
        self,
        connection_id: str | None = None,
        last_event_id: str | None = None,
        client_ip: str | None = None,
        api_key: str | None = None,
    ) -> SSEConnection:
        """
        Establish new SSE connection

        :param connection_id: Connection ID (auto-generate if None)
        :param last_event_id: Last received event ID (for reconnection)
        :param client_ip: Client IP address
        :param api_key: API key for authentication
        :return: SSE connection instance
        :raises InternalException: If connection limit is reached
        """
        # Check total connection limit
        if len(self._connections) >= self.MAX_CONNECTIONS:
            raise InternalException(
                f"Maximum connections reached: {self.MAX_CONNECTIONS}"
            )

        # Check per-IP connection limit
        if client_ip:
            ip_count = sum(
                1
                for conn in self._connections.values()
                if conn.context.context.get('client_ip') == client_ip
            )
            if ip_count >= self.MAX_CONNECTIONS_PER_IP:
                raise InternalException(
                    f"Maximum connections per IP reached: {self.MAX_CONNECTIONS_PER_IP}"
                )

        # Generate connection ID if not provided
        if not connection_id:
            connection_id = uuid.new_uuid()

        # Create async queue with size limit
        queue = asyncio.Queue(maxsize=SSEConnection.MAX_QUEUE_SIZE)

        # Create context with metadata
        context = Context(context_id=connection_id)
        context.with_value('client_ip', client_ip)
        context.with_value('api_key', api_key)
        context.with_value('last_event_id', last_event_id)

        # Create connection
        connection = SSEConnection(
            connection_id=connection_id,
            queue=queue,
            context=context,
            last_event_id=last_event_id,
        )

        # Register connection
        with self._lock:
            self._connections[connection_id] = connection

        log.request_id(connection_id).info(
            f"SSE connection established: {connection_id}, "
            f"last_event_id={last_event_id}, "
            f"client_ip={client_ip}, "
            f"total_connections={len(self._connections)}"
        )

        return connection

    async def disconnect(self, connection_id: str) -> None:
        """
        Disconnect and remove connection

        :param connection_id: Connection ID
        """
        connection = self.get_connection(connection_id)
        if connection:
            await connection.disconnect()
            with self._lock:
                self._connections.pop(connection_id, None)

            log.request_id(connection_id).info(
                f"SSE connection removed: {connection_id}, "
                f"remaining_connections={len(self._connections)}"
            )

    def get_connection(self, connection_id: str) -> SSEConnection | None:
        """
        Get connection by ID

        :param connection_id: Connection ID
        :return: Connection instance or None
        """
        with self._lock:
            return self._connections.get(connection_id)

    def get_all_connections(self) -> list[SSEConnection]:
        """
        Get all active connections

        :return: List of connections
        """
        with self._lock:
            return list(self._connections.values())

    async def broadcast(self, event: ISSEEvent) -> int:
        """
        Broadcast event to all active connections

        :param event: SSE event
        :return: Number of connections that received the event
        """
        connections = self.get_all_connections()
        active_connections = [conn for conn in connections if not conn.is_closed()]

        # Send to all active connections
        results = await asyncio.gather(
            *[conn.send(event) for conn in active_connections],
            return_exceptions=True,
        )

        # Count successful sends
        success_count = sum(1 for result in results if result is True)

        log.info(
            f"SSE broadcast: event={event.event}, "
            f"connections={len(active_connections)}, "
            f"success={success_count}"
        )

        return success_count

    def get_stats(self) -> dict:
        """
        Get global connection statistics

        :return: Statistics dict
        """
        connections = self.get_all_connections()
        return {
            'total_connections': len(connections),
            'active_connections': len([c for c in connections if not c.is_closed()]),
            'connection_stats': [conn.get_stats() for conn in connections],
            'total_dropped_events': sum(
                conn._dropped_events for conn in connections
            ),
        }


# Global connection manager instance
connection_manager = SSEConnectionManager()
