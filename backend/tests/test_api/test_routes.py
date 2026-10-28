from src.api.dependencies import check_database
from src.main import app


async def test_health_reports_connected_database(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected", "env": "test"}


async def test_health_returns_503_when_database_is_down(client):
    async def database_down() -> bool:
        return False

    app.dependency_overrides[check_database] = database_down
    try:
        response = await client.get("/health")
    finally:
        app.dependency_overrides.pop(check_database, None)
    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"


async def test_swagger_ui_and_openapi_are_served(client):
    assert (await client.get("/docs")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200


async def test_catalog_is_public(client):
    response = await client.get("/api/v1/cars")
    assert response.status_code == 200
    assert len(response.json()) > 0


async def test_unversioned_alias_serves_the_same_api(client):
    versioned = await client.get("/api/v1/motorbikes")
    alias = await client.get("/api/motorbikes")
    assert alias.status_code == 200
    assert alias.json() == versioned.json()


async def test_protected_endpoint_rejects_missing_and_invalid_token(client):
    assert (await client.get("/api/v1/conversations")).status_code == 401
    response = await client.get("/api/v1/conversations", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
