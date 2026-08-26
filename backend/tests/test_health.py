def test_api_health_returns_200(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_api_health_has_version_and_service(client):
    data = client.get("/api/v1/health").json()
    assert data["service"] == "email-productivity-agent"
    assert data["version"] == "2.0.0"


def test_health_reports_database_redis_and_external_services(client):
    data = client.get("/health").json()
    assert data["dependencies"]["database"]["status"] == "connected"
    assert data["dependencies"]["redis"] == {"status": "available", "mode": "mock"}
    assert set(data["dependencies"]["external_services"]) == {"ai", "payments", "email"}
    assert all(service["status"] == "available" for service in data["dependencies"]["external_services"].values())


def test_versioned_health_uses_operational_payload(client):
    assert client.get("/api/v1/health").json()["dependencies"] == client.get("/health").json()["dependencies"]


def test_api_health_timestamp_is_present(client):
    assert "T" in client.get("/api/v1/health").json()["timestamp"]


def test_health_route_is_in_openapi_schema(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/health" in paths


def test_unknown_route_returns_404(client):
    assert client.get("/api/v1/does-not-exist").status_code == 404
