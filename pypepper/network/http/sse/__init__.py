"""SSE (Server-Sent Events) module for PyPepper."""

from pypepper.network.http.sse.event import SSEEvent
from pypepper.network.http.sse.security import require_sse_api_key
from pypepper.network.http.sse.stream import sse_stream

__all__ = [
    "SSEEvent",
    "require_sse_api_key",
    "sse_stream",
]
