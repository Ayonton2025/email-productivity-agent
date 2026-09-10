"""Registration contract captured before splitting the mixed API router."""

import hashlib
import json
from pathlib import Path

from fastapi.routing import APIRoute, APIWebSocketRoute

from app.api import endpoints
from app.main import app


def route_contract(router):
    def dependencies(dependant):
        return [
            {
                "call": f"{item.call.__module__}.{getattr(item.call, '__qualname__', type(item.call).__qualname__)}",
                "dependencies": dependencies(item),
            }
            for item in dependant.dependencies
        ]

    return [
        {
            "path": route.path,
            "name": route.name,
            "methods": sorted(route.methods) if isinstance(route, APIRoute) else ["WEBSOCKET"],
            "operation_id": route.unique_id if isinstance(route, APIRoute) else None,
            "dependencies": dependencies(route.dependant),
        }
        for route in router.routes
        if isinstance(route, (APIRoute, APIWebSocketRoute))
    ]


def test_route_order_operations_and_dependencies_match_before_refactor():
    expected = json.loads((Path(__file__).parent / "fixtures" / "phase11_routes.json").read_text())
    assert route_contract(endpoints.router) == expected["legacy"]
    assert (
        hashlib.sha256(json.dumps(route_contract(app), sort_keys=True).encode()).hexdigest()
        == expected["direct_application_routes_sha256"]
    )


def test_compatibility_exports_are_the_registered_handlers():
    assert len(endpoints.router.routes) == 29
    for route in endpoints.router.routes:
        assert getattr(endpoints, route.name) is route.endpoint
