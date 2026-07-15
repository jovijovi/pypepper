"""
SSE (Server-Sent Events) Example Application

This example demonstrates how to use PyPepper's SSE module to create
a real-time event streaming server.

Features:
- API Key authentication
- Rate limiting
- Multiple SSE endpoints (echo, counter, clock)
- Connection statistics

Usage:
    export PYPEPPER_SSE_API_KEY=your-local-key
    python example/sse/app.py

Then connect with:
    curl -N -H "X-API-Key: $PYPEPPER_SSE_API_KEY" http://localhost:55550/sse/echo
"""

import os

from fastapi import FastAPI, Request
from fastapi.sse import EventSourceResponse

from pypepper.common import system
from pypepper.common.config import config
from pypepper.common.log import log
from pypepper.logo import logo
from pypepper.network.http.sse.connection import connection_manager
from pypepper.network.http.sse.handlers import EchoSSEHandler, CounterSSEHandler
from pypepper.network.http.sse.interfaces import ISSEConnection, ISSEHandler, ISSEEvent
from pypepper.network.http.sse.security import require_sse_api_key
from pypepper.network.http.sse.stream import sse_stream
from pypepper.scheduler.store import setup_from_config as setup_job_store_from_config
app = FastAPI(title="PyPepper SSE Example")


# Custom SSE Handler: Clock
class ClockSSEHandler(ISSEHandler):
    """Clock handler that sends current time every second"""

    async def on_connect(self, connection: ISSEConnection) -> None:
        """Send welcome message on connect"""
        from pypepper.network.http.sse.event import SSEEvent

        await connection.send(
            SSEEvent(
                data={'message': 'Clock started', 'connection_id': connection.connection_id},
                event='connect',
                id=connection.connection_id,
            )
        )

    async def on_disconnect(self, connection: ISSEConnection) -> None:
        """Log disconnect"""
        log.info(f"Clock disconnected: {connection.connection_id}")

    async def generate_events(self, connection: ISSEConnection):
        """Generate time events"""
        import asyncio
        from datetime import datetime

        from pypepper.network.http.sse.event import SSEEvent

        counter = 0
        while True:
            await asyncio.sleep(1.0)
            counter += 1
            yield SSEEvent(
                data={
                    'time': datetime.now().isoformat(),
                    'counter': counter,
                },
                event='tick',
                id=f'tick-{counter}',
            )


# SSE Endpoints
@app.get('/sse/echo')
@require_sse_api_key
async def sse_echo(request: Request):
    """
    Echo SSE endpoint - sends predefined messages

    Example:
        curl -N -H "X-API-Key: dev-api-key-123" http://localhost:55550/sse/echo
    """
    handler = EchoSSEHandler(
        messages=['Hello', 'World', 'from', 'PyPepper', 'SSE!'],
        interval=1.0,
    )
    return EventSourceResponse(sse_stream(request, handler))


@app.get('/sse/counter')
@require_sse_api_key
async def sse_counter(request: Request):
    """
    Counter SSE endpoint - counts from 0 to 100

    Example:
        curl -N -H "X-API-Key: dev-api-key-123" http://localhost:55550/sse/counter
    """
    handler = CounterSSEHandler(start=0, end=100, interval=1.0)
    return EventSourceResponse(sse_stream(request, handler))


@app.get('/sse/clock')
@require_sse_api_key
async def sse_clock(request: Request):
    """
    Clock SSE endpoint - sends current time every second

    Example:
        curl -N -H "X-API-Key: dev-api-key-123" http://localhost:55550/sse/clock
    """
    handler = ClockSSEHandler()
    return EventSourceResponse(sse_stream(request, handler))


# Utility Endpoints
@app.get('/sse/stats')
@require_sse_api_key
async def sse_stats(request: Request):
    """
    Get SSE connection statistics (auth required)

    Example:
        curl -H "X-API-Key: $PYPEPPER_SSE_API_KEY" http://localhost:55550/sse/stats
    """
    return connection_manager.get_stats()


@app.get('/health')
async def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'service': 'pypepper-sse-example'}


@app.get('/')
async def root():
    """Root endpoint with usage instructions"""
    return {
        'service': 'PyPepper SSE Example',
        'endpoints': {
            '/sse/echo': 'Echo predefined messages',
            '/sse/counter': 'Count from 0 to 100',
            '/sse/clock': 'Current time every second',
            '/sse/stats': 'Connection statistics (auth required)',
        },
        'authentication': 'Use X-API-Key or Authorization: Bearer header',
        'example': 'curl -N -H "X-API-Key: $PYPEPPER_SSE_API_KEY" http://localhost:55550/sse/echo',
    }


def _inject_demo_api_key_from_env() -> str | None:
    """Load demo API key from env into runtime config (never commit real keys)."""
    api_key = os.environ.get('PYPEPPER_SSE_API_KEY')
    if not api_key:
        return None
    sse = config.get_yml_config().sse
    keys = list(sse.authentication.validKeys or [])
    if api_key not in keys:
        keys.append(api_key)
        sse.authentication.validKeys = keys
    return api_key


def main():
    """Main entry point"""
    import uvicorn

    # Print logo and version
    log.logo(logo)

    # Handle system signals
    system.handle_signals()

    # Load configuration
    config.load_config()
    setup_job_store_from_config(config.get_yml_config())
    demo_key = _inject_demo_api_key_from_env()

    # Log SSE configuration
    sse_config = config.get_yml_config().sse
    log.info(f"SSE enabled: {sse_config.enabled}")
    log.info(f"Max connections: {sse_config.maxTotalConnections}")
    log.info(f"Authentication: {sse_config.authentication.enabled}")
    if not demo_key and sse_config.authentication.enabled:
        log.warn(
            "No PYPEPPER_SSE_API_KEY set; validKeys is empty — SSE auth will reject requests"
        )

    # Get HTTP server configuration
    network_conf = config.get_yml_config().network
    port = network_conf.httpServer.port

    log.info(f"Starting SSE example server on port {port}")
    log.info("Available endpoints:")
    log.info(f"  - http://localhost:{port}/sse/echo")
    log.info(f"  - http://localhost:{port}/sse/counter")
    log.info(f"  - http://localhost:{port}/sse/clock")
    log.info(f"  - http://localhost:{port}/sse/stats")
    log.info("")
    log.info("Example usage:")
    log.info('  export PYPEPPER_SSE_API_KEY=your-local-key')
    log.info(
        f'  curl -N -H "X-API-Key: $PYPEPPER_SSE_API_KEY" http://localhost:{port}/sse/echo'
    )

    # Run server
    uvicorn.run(app, host='0.0.0.0', port=port, timeout_keep_alive=30)


if __name__ == '__main__':
    main()
