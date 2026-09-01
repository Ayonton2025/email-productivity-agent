"""Request correlation middleware for structured application logs."""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started = time.perf_counter()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "http_request_completed",
                duration_ms=duration_ms,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
            )
            return response
        except Exception:
            logger.exception(
                "http_request_failed",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                method=request.method,
                path=request.url.path,
            )
            raise
        finally:
            structlog.contextvars.clear_contextvars()


def register_request_logging(app) -> None:
    app.add_middleware(RequestLoggingMiddleware)
