from functools import wraps
from typing import Any, Callable

from fastapi import Request, HTTPException, status

from pypepper.common.cache import Cache
from pypepper.common.config import config


class SSESecurityManager:
    """SSE Security Manager (API Key authentication + Rate limiting)"""

    # Rate limit cache (TTL 60 seconds)
    _rate_limit_cache = Cache(maxsize=1000, ttl=60)

    @staticmethod
    def validate_api_key(api_key: str | None) -> bool:
        """
        Validate API Key

        :param api_key: API Key
        :return: True if valid
        """
        if not api_key:
            return False

        # Get valid API keys from config
        sse_config = config.get_yml_config().sse
        if not sse_config.authentication.enabled:
            # Authentication disabled, allow all
            return True

        valid_keys = sse_config.authentication.validKeys
        return api_key in valid_keys

    @staticmethod
    def check_rate_limit(client_id: str) -> bool:
        """
        Check rate limit (simple counter)

        :param client_id: Client identifier (API Key or IP)
        :return: True if within limit
        """
        sse_config = config.get_yml_config().sse

        if not sse_config.rateLimit.enabled:
            # Rate limit disabled, allow all
            return True

        max_requests = sse_config.rateLimit.maxRequestsPerMinute
        key = f'rate_limit:{client_id}'
        count = SSESecurityManager._rate_limit_cache.get(key) or 0

        if count >= max_requests:
            return False

        SSESecurityManager._rate_limit_cache.set(key, count + 1)
        return True


def require_sse_api_key(func: Callable) -> Callable:
    """
    API Key authentication decorator

    Supports three ways to pass API Key:
    1. Header: X-API-Key: your-key
    2. Query: ?api_key=your-key
    3. Header: Authorization: Bearer your-key

    Usage:
        @app.get('/sse')
        @require_sse_api_key
        async def sse_endpoint(request: Request):
            ...
    """

    @wraps(func)
    async def wrapper(request: Request, *args: Any, **kwargs: Any):
        # Extract API Key from request
        api_key = (
            request.headers.get('X-API-Key')
            or request.query_params.get('api_key')
            or request.headers.get('Authorization', '').replace('Bearer ', '').strip()
        )

        # Validate API Key
        if not SSESecurityManager.validate_api_key(api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid or missing API key',
                headers={'WWW-Authenticate': 'Bearer'},
            )

        # Rate limit check
        client_id = api_key  # Use API Key as client identifier
        if not SSESecurityManager.check_rate_limit(client_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail='Rate limit exceeded (max 60 requests/minute)',
            )

        # Store metadata in request state for later use
        request.state.api_key = api_key
        request.state.client_ip = request.client.host

        return await func(request, *args, **kwargs)

    return wrapper
