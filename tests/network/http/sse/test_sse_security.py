from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from pypepper.common.cache import Cache
from pypepper.common.config import config
from pypepper.network.http.sse.security import SSESecurityManager, require_sse_api_key


def _build_sse_config(
    auth_enabled: bool = True,
    valid_keys: list[str] | None = None,
    rate_enabled: bool = True,
    max_requests: int = 60,
):
    return SimpleNamespace(
        sse=SimpleNamespace(
            authentication=SimpleNamespace(
                enabled=auth_enabled,
                validKeys=valid_keys or ['test-key'],
            ),
            rateLimit=SimpleNamespace(
                enabled=rate_enabled,
                maxRequestsPerMinute=max_requests,
            ),
        )
    )


def _mock_request(
    headers: dict | None = None,
    query_params: dict | None = None,
    client_host: str = '127.0.0.1',
):
    return SimpleNamespace(
        headers=headers or {},
        query_params=query_params or {},
        state=SimpleNamespace(),
        client=SimpleNamespace(host=client_host),
    )


@pytest.fixture(autouse=True)
def _reset_rate_limit_cache():
    SSESecurityManager._rate_limit_cache = Cache(maxsize=1000, ttl=60)


def test_validate_api_key_returns_false_for_empty_key(monkeypatch):
    monkeypatch.setattr(config, 'get_yml_config', lambda: _build_sse_config())
    assert SSESecurityManager.validate_api_key(None) is False
    assert SSESecurityManager.validate_api_key('') is False


def test_validate_api_key_allows_any_key_when_auth_disabled(monkeypatch):
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(auth_enabled=False),
    )
    assert SSESecurityManager.validate_api_key('any-key') is True


def test_validate_api_key_checks_allow_list_when_auth_enabled(monkeypatch):
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(auth_enabled=True, valid_keys=['k1', 'k2']),
    )
    assert SSESecurityManager.validate_api_key('k1') is True
    assert SSESecurityManager.validate_api_key('invalid') is False


def test_check_rate_limit_allows_all_when_disabled(monkeypatch):
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(rate_enabled=False),
    )
    assert SSESecurityManager.check_rate_limit('client-a') is True
    assert SSESecurityManager.check_rate_limit('client-a') is True


def test_check_rate_limit_blocks_requests_over_limit(monkeypatch):
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(rate_enabled=True, max_requests=2),
    )
    assert SSESecurityManager.check_rate_limit('client-a') is True
    assert SSESecurityManager.check_rate_limit('client-a') is True
    assert SSESecurityManager.check_rate_limit('client-a') is False
    assert SSESecurityManager.check_rate_limit('client-b') is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('headers', 'query_params', 'expected_key'),
    [
        ({'X-API-Key': 'header-key'}, {}, 'header-key'),
        ({}, {'api_key': 'query-key'}, 'query-key'),
        ({'Authorization': 'Bearer bearer-key'}, {}, 'bearer-key'),
    ],
)
async def test_require_sse_api_key_accepts_multiple_key_sources(
    monkeypatch,
    headers,
    query_params,
    expected_key,
):
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(valid_keys=['header-key', 'query-key', 'bearer-key']),
    )

    @require_sse_api_key
    async def handler(request, value):
        return {'ok': True, 'value': value}

    request = _mock_request(headers=headers, query_params=query_params, client_host='10.0.0.1')
    result = await handler(request, 42)

    assert result == {'ok': True, 'value': 42}
    assert request.state.api_key == expected_key
    assert request.state.client_ip == '10.0.0.1'


@pytest.mark.asyncio
async def test_require_sse_api_key_raises_401_for_invalid_or_missing_key(monkeypatch):
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(valid_keys=['valid-key']),
    )

    @require_sse_api_key
    async def handler(request):
        return {'ok': True}

    with pytest.raises(HTTPException) as exc_info:
        await handler(_mock_request(headers={}))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Invalid or missing API key'
    assert exc_info.value.headers == {'WWW-Authenticate': 'Bearer'}


@pytest.mark.asyncio
async def test_require_sse_api_key_raises_429_when_rate_limit_exceeded(monkeypatch):
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(valid_keys=['limited-key'], max_requests=1),
    )

    @require_sse_api_key
    async def handler(request):
        return {'ok': True}

    request = _mock_request(headers={'X-API-Key': 'limited-key'})
    first = await handler(request)
    assert first == {'ok': True}

    with pytest.raises(HTTPException) as exc_info:
        await handler(request)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == 'Rate limit exceeded (max 60 requests/minute)'
