from fastapi.testclient import TestClient

from pypepper.network.http.server import create_app


def test_health_and_ping_endpoints():
    app = create_app(None)
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


def test_create_app_does_not_stack_routes_across_instances():
    app1 = create_app(None)
    app2 = create_app(None)
    paths1 = [getattr(r, "path", None) for r in app1.routes]
    paths2 = [getattr(r, "path", None) for r in app2.routes]
    assert paths1.count("/health") == 1
    assert paths2.count("/health") == 1
    assert paths1.count("/ping") == 1
    assert paths1.count("/metrics") == 1
