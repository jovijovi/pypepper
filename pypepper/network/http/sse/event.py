from __future__ import annotations

from typing import Any

from fastapi.sse import ServerSentEvent

from pypepper.event.event import Event
from pypepper.network.http.sse.interfaces import ISSEEvent


class SSEEvent(ISSEEvent):
    """
    SSE Event wrapper
    Compatible with PyPepper Event and FastAPI ServerSentEvent
    """

    def __init__(
        self,
        data: Any = None,
        raw_data: str | None = None,
        event: str | None = None,
        id: str | None = None,
        retry: int | None = None,
        comment: str | None = None,
    ):
        """
        Initialize SSE event

        :param data: JSON-serializable data (mutually exclusive with raw_data)
        :param raw_data: Raw string data (mutually exclusive with data)
        :param event: Event type name
        :param id: Event ID (for reconnection)
        :param retry: Reconnection interval in milliseconds
        :param comment: Comment line (for keep-alive heartbeat)
        """
        self.data = data
        self.raw_data = raw_data
        self.event = event
        self.id = id
        self.retry = retry
        self.comment = comment

    def to_server_sent_event(self) -> ServerSentEvent:
        """
        Convert to FastAPI ServerSentEvent
        :return: ServerSentEvent instance
        """
        return ServerSentEvent(
            data=self.data,
            raw_data=self.raw_data,
            event=self.event,
            id=self.id,
            retry=self.retry,
            comment=self.comment,
        )

    @classmethod
    def from_pypepper_event(
        cls,
        event: Event,
        event_type: str | None = None,
    ) -> SSEEvent:
        """
        Convert from PyPepper Event

        :param event: PyPepper Event object
        :param event_type: SSE event type (defaults to event.data.name)
        :return: SSEEvent instance
        """
        return cls(
            data={
                'header': {
                    'namespace': event.data.header.namespace,
                    'request_id': event.data.header.request_id,
                    'sender': event.data.header.sender,
                    'id': event.data.header.id,
                    'timestamp': str(event.data.header.timestamp),
                    'version': event.data.header.version,
                },
                'flow': event.data.flow,
                'name': event.data.name,
                'src': event.data.src,
                'payload': {
                    'id': event.data.payload.id,
                    'category': event.data.payload.category,
                    'raw': (
                        event.data.payload.raw.decode()
                        if isinstance(event.data.payload.raw, bytes)
                        else event.data.payload.raw
                    ),
                },
            },
            event=event_type or event.data.name,
            id=event.data.header.id,
        )

    @staticmethod
    def ping(comment: str = "heartbeat") -> SSEEvent:
        """
        Create heartbeat event
        :param comment: Comment text
        :return: SSEEvent instance
        """
        return SSEEvent(comment=comment)

    @staticmethod
    def reconnect(retry_ms: int = 3000) -> SSEEvent:
        """
        Create reconnection configuration event
        :param retry_ms: Retry interval in milliseconds
        :return: SSEEvent instance
        """
        return SSEEvent(retry=retry_ms)


def new_sse_event(
    data: Any = None,
    event: str | None = None,
    id: str | None = None,
) -> SSEEvent:
    """
    Create SSE event

    :param data: Event data
    :param event: Event type
    :param id: Event ID
    :return: SSEEvent instance
    """
    return SSEEvent(data=data, event=event, id=id)
