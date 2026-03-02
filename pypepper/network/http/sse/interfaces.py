from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import AsyncIterable

from pypepper.common.context import Context


class ISSEEvent(metaclass=ABCMeta):
    """SSE Event interface"""

    @abstractmethod
    def to_server_sent_event(self) -> 'ServerSentEvent':
        """
        Convert to FastAPI ServerSentEvent
        :return: ServerSentEvent instance
        """
        pass


class ISSEConnection(metaclass=ABCMeta):
    """SSE Connection interface"""

    connection_id: str
    context: Context
    last_event_id: str | None

    @abstractmethod
    async def send(self, event: ISSEEvent) -> bool:
        """
        Send event to client
        :param event: SSE event
        :return: True if sent successfully
        """
        pass

    @abstractmethod
    async def ping(self) -> None:
        """Send heartbeat to keep connection alive"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect and cleanup resources"""
        pass

    @abstractmethod
    def is_closed(self) -> bool:
        """
        Check if connection is closed
        :return: True if closed
        """
        pass


class ISSEConnectionManager(metaclass=ABCMeta):
    """SSE Connection Manager interface"""

    @abstractmethod
    async def connect(
        self,
        connection_id: str | None = None,
        last_event_id: str | None = None,
        client_ip: str | None = None,
        api_key: str | None = None,
    ) -> ISSEConnection:
        """
        Establish new SSE connection
        :param connection_id: Connection ID (auto-generate if None)
        :param last_event_id: Last received event ID (for reconnection)
        :param client_ip: Client IP address
        :param api_key: API key for authentication
        :return: SSE connection instance
        """
        pass

    @abstractmethod
    async def disconnect(self, connection_id: str) -> None:
        """
        Disconnect and remove connection
        :param connection_id: Connection ID
        """
        pass

    @abstractmethod
    def get_connection(self, connection_id: str) -> ISSEConnection | None:
        """
        Get connection by ID
        :param connection_id: Connection ID
        :return: Connection instance or None
        """
        pass

    @abstractmethod
    def get_all_connections(self) -> list[ISSEConnection]:
        """
        Get all active connections
        :return: List of connections
        """
        pass

    @abstractmethod
    async def broadcast(self, event: ISSEEvent) -> int:
        """
        Broadcast event to all active connections
        :param event: SSE event
        :return: Number of connections that received the event
        """
        pass


class ISSEHandler(metaclass=ABCMeta):
    """SSE Handler interface"""

    @abstractmethod
    async def on_connect(self, connection: ISSEConnection) -> None:
        """
        Called when client connects
        :param connection: SSE connection
        """
        pass

    @abstractmethod
    async def on_disconnect(self, connection: ISSEConnection) -> None:
        """
        Called when client disconnects
        :param connection: SSE connection
        """
        pass

    @abstractmethod
    async def generate_events(
        self,
        connection: ISSEConnection,
    ) -> AsyncIterable[ISSEEvent]:
        """
        Generate events for the connection (async generator)
        :param connection: SSE connection
        :return: Async iterable of SSE events
        """
        pass
