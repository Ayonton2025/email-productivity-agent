from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import security_middleware


def _build_app(monkeypatch, rate_limit: str = "2/minute") -> FastAPI:
    monkeypatch.setattr(security_middleware.settings, "RATE_LIMIT_DEFAULT", rate_limit)
    monkeypatch.setattr(security_middleware.settings, "TRUSTED_HOSTS", "testserver,api.example.com")
    test_app = FastAPI()
    security_middleware.register_security_middleware(test_app)

    @test_app.get("/probe")
    async def probe():
        return {"ok": True}

    return test_app


def test_trusted_hosts_reject_unlisted_host(monkeypatch):
    with TestClient(_build_app(monkeypatch)) as client:
        response = client.get("/probe", headers={"Host": "attacker.example"})
    assert response.status_code == 400


def test_default_rate_limit_applies_to_all_routes(monkeypatch):
    with TestClient(_build_app(monkeypatch)) as client:
        assert client.get("/probe").status_code == 200
        assert client.get("/probe").status_code == 200
        response = client.get("/probe")
    assert response.status_code == 429
    assert response.headers["Retry-After"]
