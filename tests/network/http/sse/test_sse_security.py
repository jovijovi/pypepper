from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from pypepper.common.cache import Cache
from pypepper.common.config import config
from pypepper.network.http.sse.security import (
    AUTH_OFF_BLOCKED_DETAIL,
    SSESecurityManager,
    require_sse_api_key,
)


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
def _reset_rate_limit_cache(monkeypatch):
    from pypepper.network.http.sse import security as sse_security

    SSESecurityManager._rate_limit_cache = Cache(maxsize=1000, ttl=60)
    sse_security.reset_auth_disabled_warning()
    monkeypatch.delenv('PYPEPPER_SSE_ALLOW_AUTH_OFF', raising=False)


def test_validate_api_key_returns_false_for_empty_key(monkeypatch):
    monkeypatch.setattr(config, 'get_yml_config', lambda: _build_sse_config())
    assert SSESecurityManager.validate_api_key(None) is False
    assert SSESecurityManager.validate_api_key('') is False


def test_auth_disabled_empty_key_does_not_warn(monkeypatch):
    from pypepper.common.log import log
    from pypepper.network.http.sse import security as sse_security

    warns: list[str] = []
    monkeypatch.setattr(log, 'warn', lambda msg, *a, **k: warns.append(str(msg)))
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(auth_enabled=False),
    )
    sse_security.reset_auth_disabled_warning()
    assert SSESecurityManager.validate_api_key(None) is False
    assert SSESecurityManager.validate_api_key('') is False
    assert warns == []


def test_validate_api_key_rejects_when_auth_disabled_without_escape(monkeypatch):
    from pypepper.common.log import log
    from pypepper.network.http.sse import security as sse_security

    warns: list[str] = []
    monkeypatch.setattr(log, 'warn', lambda msg, *a, **k: warns.append(str(msg)))
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(auth_enabled=False),
    )
    sse_security.reset_auth_disabled_warning()
    assert SSESecurityManager.validate_api_key('any-key') is False
    assert any('PYPEPPER_SSE_ALLOW_AUTH_OFF' in w for w in warns)
    # Second call does not spam another warn.
    warns.clear()
    assert SSESecurityManager.validate_api_key('other-key') is False
    assert warns == []


def test_validate_api_key_allows_any_key_when_auth_disabled_with_escape(monkeypatch):
    from pypepper.common.log import log
    from pypepper.network.http.sse import security as sse_security

    warns: list[str] = []
    monkeypatch.setattr(log, 'warn', lambda msg, *a, **k: warns.append(str(msg)))
    monkeypatch.setenv('PYPEPPER_SSE_ALLOW_AUTH_OFF', '1')
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(auth_enabled=False),
    )
    sse_security.reset_auth_disabled_warning()
    assert SSESecurityManager.validate_api_key('any-key') is True
    assert any('authentication.enabled is false' in w for w in warns)
    # Second call does not spam another warn.
    warns.clear()
    assert SSESecurityManager.validate_api_key('other-key') is True
    assert warns == []


@pytest.mark.parametrize('escape_value', ['true', 'YES', 'On'])
def test_auth_off_escape_env_truthy_values(monkeypatch, escape_value):
    monkeypatch.setenv('PYPEPPER_SSE_ALLOW_AUTH_OFF', escape_value)
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(auth_enabled=False),
    )
    assert SSESecurityManager.validate_api_key('k') is True


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
    ('headers', 'expected_key'),
    [
        ({'X-API-Key': 'header-key'}, 'header-key'),
        ({'Authorization': 'Bearer bearer-key'}, 'bearer-key'),
    ],
)
async def test_require_sse_api_key_accepts_header_sources(
    monkeypatch,
    headers,
    expected_key,
):
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(valid_keys=['header-key', 'bearer-key']),
    )

    @require_sse_api_key
    async def handler(request, value):
        return {'ok': True, 'value': value}

    request = _mock_request(headers=headers, client_host='10.0.0.1')
    result = await handler(request, 42)

    assert result == {'ok': True, 'value': 42}
    assert request.state.api_key == expected_key
    assert request.state.client_ip == '10.0.0.1'


@pytest.mark.asyncio
async def test_require_sse_api_key_rejects_query_string_key(monkeypatch):
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(valid_keys=['query-key']),
    )

    @require_sse_api_key
    async def handler(request):
        return {'ok': True}

    with pytest.raises(HTTPException) as exc_info:
        await handler(_mock_request(query_params={'api_key': 'query-key'}))

    assert exc_info.value.status_code == 401


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
async def test_require_sse_api_key_raises_503_when_auth_off_without_escape(monkeypatch):
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(auth_enabled=False),
    )

    @require_sse_api_key
    async def handler(request):
        return {'ok': True}

    with pytest.raises(HTTPException) as exc_info:
        await handler(_mock_request(headers={'X-API-Key': 'any-key'}))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == AUTH_OFF_BLOCKED_DETAIL


@pytest.mark.asyncio
async def test_require_sse_api_key_allows_auth_off_with_escape(monkeypatch):
    monkeypatch.setenv('PYPEPPER_SSE_ALLOW_AUTH_OFF', '1')
    monkeypatch.setattr(
        config,
        'get_yml_config',
        lambda: _build_sse_config(auth_enabled=False),
    )

    @require_sse_api_key
    async def handler(request):
        return {'ok': True}

    request = _mock_request(headers={'X-API-Key': 'any-key'})
    assert await handler(request) == {'ok': True}
    assert request.state.api_key == 'any-key'


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
    assert exc_info.value.detail == 'Rate limit exceeded (max 1 requests/minute)'
