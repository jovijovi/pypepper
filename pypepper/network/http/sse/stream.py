from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterable

from fastapi import Request
from fastapi.sse import ServerSentEvent

from pypepper.common.log import log
from pypepper.network.http.sse.connection import SSEConnection, connection_manager
from pypepper.network.http.sse.interfaces import ISSEHandler


def _serialize_sse_event(event: ServerSentEvent) -> str:
    """
    Serialize ServerSentEvent to SSE format string

    SSE format:
    event: event_type
    id: event_id
    retry: milliseconds
    data: json_data
    :comment

    :param event: ServerSentEvent object
    :return: SSE formatted string
    """
    lines = []

    if event.comment:
        lines.append(f':{event.comment}')

    if event.event:
        lines.append(f'event: {event.event}')

    if event.id:
        lines.append(f'id: {event.id}')

    if event.retry is not None:
        lines.append(f'retry: {event.retry}')

    if event.raw_data is not None:
        # Raw data mode: send as-is
        for line in event.raw_data.splitlines():
            lines.append(f'data: {line}')
    elif event.data is not None:
        # JSON mode: serialize data
        data_str = json.dumps(event.data, ensure_ascii=False)
        lines.append(f'data: {data_str}')

    # SSE spec: events are separated by double newline
    return '\n'.join(lines) + '\n\n'


async def sse_stream(
    request: Request,
    handler: ISSEHandler,
    connection_id: str | None = None,
) -> AsyncIterable[str]:
    """
    SSE stream generator

    Yields SSE-formatted strings ready for transmission.

    :param request: FastAPI Request object
    :param handler: SSE handler
    :param connection_id: Connection ID (optional, auto-generate if None)
    :return: AsyncIterable of SSE-formatted strings
    """
    # Extract metadata from request
    last_event_id = request.headers.get('Last-Event-ID')
    client_ip = getattr(request.state, 'client_ip', request.client.host)
    api_key = getattr(request.state, 'api_key', None)

    # Establish connection
    connection = await connection_manager.connect(
        connection_id=connection_id,
        last_event_id=last_event_id,
        client_ip=client_ip,
        api_key=api_key,
    )

    try:
        # Trigger on_connect callback
        await handler.on_connect(connection)

        # Create event generation task
        event_gen_task = asyncio.create_task(
            _consume_handler_events(handler, connection)
        )

        # Stream events from queue
        while not await request.is_disconnected():
            try:
                # Wait for event with timeout (for heartbeat)
                event = await asyncio.wait_for(
                    connection._queue.get(),
                    timeout=30.0,  # 30 seconds timeout
                )

                # Convert to ServerSentEvent and serialize to SSE format
                sse_event = event.to_server_sent_event()
                yield _serialize_sse_event(sse_event)

            except asyncio.TimeoutError:
                # Timeout: send heartbeat
                from pypepper.network.http.sse.event import SSEEvent

                sse_event = SSEEvent.ping().to_server_sent_event()
                yield _serialize_sse_event(sse_event)
                continue

            except Exception as e:
                log.error(f"SSE stream error: {e}")
                break

        # Cancel event generation task
        event_gen_task.cancel()
        try:
            await event_gen_task
        except asyncio.CancelledError:
            pass

    finally:
        # Trigger on_disconnect callback
        await handler.on_disconnect(connection)

        # Cleanup connection
        await connection_manager.disconnect(connection.connection_id)


async def _consume_handler_events(
    handler: ISSEHandler,
    connection: SSEConnection,
) -> None:
    """
    Consume events from handler and send to connection

    :param handler: SSE handler
    :param connection: SSE connection
    """
    try:
        async for event in handler.generate_events(connection):
            await connection.send(event)
    except asyncio.CancelledError:
        # Task cancelled, exit gracefully
        pass
    except Exception as e:
        log.error(f"Handler event generation error: {e}")
