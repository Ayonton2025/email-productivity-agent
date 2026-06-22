"""
Utilities for running async task bodies from sync Celery task wrappers.

Using asyncio.run() per task creates a new event loop each invocation, which
can break pooled async DB connections (asyncpg) with "different loop" errors.
"""

import asyncio
import threading
from typing import Any


_state = threading.local()


def _get_loop() -> asyncio.AbstractEventLoop:
    loop = getattr(_state, "loop", None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        _state.loop = loop
    return loop


def run_async(awaitable: Any) -> Any:
    loop = _get_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(awaitable)
