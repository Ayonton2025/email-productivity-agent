"""Request correlation middleware for structured application logs."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "HTTP request completed",
            extra={
                "request_id": request_id,
                "duration_ms": duration_ms,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            },
        )
        return response


def register_request_logging(app) -> None:
    app.add_middleware(RequestLoggingMiddleware)
