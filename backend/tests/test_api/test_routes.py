import pytest


@pytest.mark.asyncio
async def test_health_reports_database_connection(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"


@pytest.mark.asyncio
async def test_catalog_is_public(client):
    response = await client.get("/api/v1/cars")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_protected_endpoint_rejects_missing_token(client):
    response = await client.get("/api/v1/conversations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_rejects_invalid_token(client):
    response = await client.get(
        "/api/v1/conversations",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
