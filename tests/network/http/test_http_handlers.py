from fastapi.testclient import TestClient

from pypepper.network.http.handlers import handlers
from pypepper.network.http.server import app


def test_health_and_ping_endpoints():
    handlers.register_handlers(app, None)
    handlers.use_middleware(app, None)
    client = TestClient(app)

    ping = client.get('/ping')
    assert ping.status_code == 200
    assert ping.text == '"pong"' or ping.json() == 'pong' or ping.text.strip('"') == 'pong'

    health = client.get('/health')
    assert health.status_code == 200
    body = health.json()
    assert body['code'] == '200'
    assert 'data' in body

    metrics = client.get('/metrics')
    assert metrics.status_code == 200
    mbody = metrics.json()
    assert 'uptime_seconds' in mbody['data']
    assert 'X-Request-ID' in metrics.headers
