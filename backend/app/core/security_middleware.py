"""Central registration for HTTP boundary protections."""

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings


def register_security_middleware(app: FastAPI) -> Limiter:
    """Enable trusted-host enforcement and IP-based default rate limits."""
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[settings.RATE_LIMIT_DEFAULT],
        headers_enabled=True,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.get_trusted_hosts())
    return limiter
