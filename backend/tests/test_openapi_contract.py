import pytest


@pytest.mark.asyncio
async def test_openapi_contains_required_rest_methods(client):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    methods = {method for operations in paths.values() for method in operations}
    assert {"get", "post", "delete"} <= methods


@pytest.mark.asyncio
async def test_openapi_exposes_human_chat_and_no_deprecated_chat_endpoint(client):
    paths = (await client.get("/openapi.json")).json()["paths"]
    assert "/api/v1/conversations" in paths
    assert "/api/v1/conversations/{conversation_id}/messages" in paths
    assert "/api/v1/chat" not in paths
    assert "/api/v1/status" not in paths
