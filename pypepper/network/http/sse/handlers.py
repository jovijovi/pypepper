from collections.abc import AsyncIterable

from pypepper.network.http.sse.event import SSEEvent
from pypepper.network.http.sse.interfaces import ISSEConnection, ISSEHandler, ISSEEvent


class BaseSSEHandler(ISSEHandler):
    """Base SSE Handler (default implementation)"""

    async def on_connect(self, connection: ISSEConnection) -> None:
        """
        Called when client connects

        :param connection: SSE connection
        """
        # Send welcome message
        await connection.send(
            SSEEvent(
                data={
                    'message': 'Connected',
                    'connection_id': connection.connection_id,
                },
                event='connect',
                id=connection.connection_id,
            )
        )

    async def on_disconnect(self, connection: ISSEConnection) -> None:
        """
        Called when client disconnects

        :param connection: SSE connection
        """
        # Default: no action on disconnect
        pass

    async def generate_events(
        self,
        connection: ISSEConnection,
    ) -> AsyncIterable[ISSEEvent]:
        """
        Generate events for the connection (default: no events)

        :param connection: SSE connection
        :return: Async iterable of SSE events
        """
        # Default: no events generated
        # Subclasses should override this method
        return
        yield  # Make it a generator


class EchoSSEHandler(BaseSSEHandler):
    """Echo SSE Handler (for testing)"""

    def __init__(self, messages: list[str] | None = None, interval: float = 1.0):
        """
        Initialize Echo handler

        :param messages: List of messages to echo
        :param interval: Interval between messages (seconds)
        """
        self.messages = messages or ['Hello', 'World', 'SSE', 'Test']
        self.interval = interval

    async def generate_events(
        self,
        connection: ISSEConnection,
    ) -> AsyncIterable[ISSEEvent]:
        """
        Generate echo events

        :param connection: SSE connection
        :return: Async iterable of SSE events
        """
        import asyncio

        for i, msg in enumerate(self.messages):
            await asyncio.sleep(self.interval)
            yield SSEEvent(
                data={'message': msg, 'index': i},
                event='echo',
                id=f'echo-{i}',
            )


class CounterSSEHandler(BaseSSEHandler):
    """Counter SSE Handler (counting example)"""

    def __init__(self, start: int = 0, end: int = 10, interval: float = 1.0):
        """
        Initialize Counter handler

        :param start: Start value
        :param end: End value
        :param interval: Interval between counts (seconds)
        """
        self.start = start
        self.end = end
        self.interval = interval

    async def generate_events(
        self,
        connection: ISSEConnection,
    ) -> AsyncIterable[ISSEEvent]:
        """
        Generate counter events

        :param connection: SSE connection
        :return: Async iterable of SSE events
        """
        import asyncio

        for count in range(self.start, self.end + 1):
            await asyncio.sleep(self.interval)
            yield SSEEvent(
                data={'count': count},
                event='counter',
                id=f'count-{count}',
            )
