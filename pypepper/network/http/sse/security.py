"""SSE API key authentication helpers."""

from collections.abc import Callable
from functools import wraps
from hmac import compare_digest
from threading import Lock
from typing import Any

from fastapi import HTTPException, Request, status

from pypepper.common.cache import Cache
from pypepper.common.config import config
from pypepper.common.log import log

_auth_disabled_warned = False


def _warn_auth_disabled_once() -> None:
    """Log once that auth-off accepts any non-empty key and is not a security boundary."""
    global _auth_disabled_warned
    if _auth_disabled_warned:
        return
    _auth_disabled_warned = True
    log.warn(
        "sse.authentication.enabled is false: any non-empty API key is accepted; "
        "rate limiting buckets by presented key and is not a security boundary. "
        "Enable authentication and inject validKeys for production."
    )


def reset_auth_disabled_warning() -> None:
    """Reset the one-shot auth-off warning (tests)."""
    global _auth_disabled_warned
    _auth_disabled_warned = False


class SSESecurityManager:
    """SSE Security Manager (API Key authentication + Rate limiting)"""

    # Rate limit cache (TTL 60 seconds)
    _rate_limit_cache = Cache(maxsize=1000, ttl=60)
    _rate_limit_lock = Lock()

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
            # Authentication disabled, allow all non-empty keys
            _warn_auth_disabled_once()
            return True

        valid_keys = list(sse_config.authentication.validKeys or [])
        return any(compare_digest(api_key, key) for key in valid_keys if isinstance(key, str))

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
        key = f"rate_limit:{client_id}"

        with SSESecurityManager._rate_limit_lock:
            count = SSESecurityManager._rate_limit_cache.get(key) or 0
            if count >= max_requests:
                return False
            SSESecurityManager._rate_limit_cache.set(key, count + 1)
            return True


def require_sse_api_key(func: Callable) -> Callable:
    """
    API Key authentication decorator

    Supports:
    1. Header: X-API-Key: your-key
    2. Header: Authorization: Bearer your-key

    Query-string API keys are rejected to avoid log/Referer leakage.

    Usage:
        @app.get('/sse')
        @require_sse_api_key
        async def sse_endpoint(request: Request):
            ...
    """

    @wraps(func)
    async def wrapper(request: Request, *args: Any, **kwargs: Any):
        authorization = request.headers.get("Authorization", "")
        bearer = ""
        if authorization.lower().startswith("bearer "):
            bearer = authorization[7:].strip()

        api_key = request.headers.get("X-API-Key") or bearer or None

        # Validate API Key
        if not SSESecurityManager.validate_api_key(api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Rate limit check
        client_id = api_key or ""
        if not SSESecurityManager.check_rate_limit(client_id):
            sse_config = config.get_yml_config().sse
            max_requests = sse_config.rateLimit.maxRequestsPerMinute
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded (max {max_requests} requests/minute)",
            )

        # Store metadata in request state for later use
        request.state.api_key = api_key
        request.state.client_ip = request.client.host if request.client is not None else None

        return await func(request, *args, **kwargs)

    return wrapper
