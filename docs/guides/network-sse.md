# Network and SSE

HTTP server is FastAPI + uvicorn. SSE adds connection management, auth, and rate limiting.

## HTTP server

Implement `ITaskHandler` and call `server.run`:

```python
from fastapi import FastAPI

from pypepper.common.config import config
from pypepper.network.http import server
from pypepper.network.http.interfaces import ITaskHandler


class AppHandlers(ITaskHandler):
    def register_handlers(self, app: FastAPI):
        @app.get("/hello")
        def hello():
            return {"msg": "ok"}

    def use_middleware(self, app: FastAPI):
        pass


config.load_config("./conf/app.config.yaml")
server.run(AppHandlers())
```

Built-in routes from `BaseHandlers`: `/health`, `/ping`, `/metrics`.
`RequestIdMiddleware` injects `X-Request-ID`.

TLS uses `network.httpsServer` (`certFile` / `keyFile` / optional `caFile` for mTLS).

## SSE handler

```python
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.sse import EventSourceResponse

from pypepper.network.http.sse.event import SSEEvent
from pypepper.network.http.sse.interfaces import ISSEConnection, ISSEEvent, ISSEHandler
from pypepper.network.http.sse.security import require_sse_api_key
from pypepper.network.http.sse.stream import sse_stream


class ClockSSEHandler(ISSEHandler):
    async def on_connect(self, connection: ISSEConnection) -> None:
        await connection.send(SSEEvent(data={"status": "connected"}, event="connect"))

    async def on_disconnect(self, connection: ISSEConnection) -> None:
        return

    async def generate_events(self, connection: ISSEConnection) -> AsyncIterator[ISSEEvent]:
        yield SSEEvent(data={"tick": 1}, event="tick", id="1")


app = FastAPI()


@app.get("/sse/clock")
@require_sse_api_key
async def clock(request: Request):
    return EventSourceResponse(sse_stream(request, ClockSSEHandler()))
```

## Auth and limits

- Headers only: `X-API-Key` or `Authorization: Bearer <key>`
- Query-string `api_key` is rejected
- Keys come from YAML `sse.authentication.validKeys` (default empty — inject via deployment)
- Rate limit: `sse.rateLimit.maxRequestsPerMinute`
- Connection caps: `maxTotalConnections`, `maxConnectionsPerIP`

### Security notes

- **Production:** keep `sse.authentication.enabled: true` and inject `validKeys` (do not commit real keys).
- **Auth off is not anonymous access.** When `authentication.enabled` is `false`, any **non-empty** API key is accepted. The library logs a **one-shot** warning (once per process) when this path is used.
- **Rate limiting is not a security boundary when auth is off.** Limits are bucketed by the presented key string, so clients can rotate keys to bypass quotas. Treat rate limits as abuse soft-control only when authentication is enabled.

See the full working app in [`example/sse/app.py`](https://github.com/jovijovi/pypepper/blob/main/example/sse/app.py).

```shell
export PYPEPPER_SSE_API_KEY=your-local-key
python example/sse/app.py
curl -N -H "X-API-Key: $PYPEPPER_SSE_API_KEY" http://localhost:55550/sse/echo
```

See also: [API Reference / Network and SSE](../reference/network.md).
