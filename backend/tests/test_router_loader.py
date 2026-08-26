from fastapi import APIRouter

from app.api.system_endpoints import RuntimeContext, create_system_router
from app.core.router_loader import RouterSpec, load_router


def test_router_spec_name_includes_attribute():
    assert RouterSpec("app.api.example", "custom").name == "app.api.example.custom"


def test_load_router_returns_none_for_missing_module():
    assert load_router(RouterSpec("app.api.does_not_exist")) is None


def test_load_router_accepts_router_attribute():
    module = "app.api.system_endpoints"
    runtime = RuntimeContext([], False, 8000, set(), lambda: True)
    router = create_system_router(runtime)
    assert isinstance(router, APIRouter)
