"""The published OpenAPI document is the contract; verify it against runtime behavior."""

import re
import uuid

import pytest

JSON = "application/json"
MULTIPART = "multipart/form-data"
# The only endpoints allowed to take something other than JSON: binary image uploads.
MULTIPART_ENDPOINTS = {
    ("post", "/api/v1/cars/{car_id}/image"),
    ("post", "/api/v1/motorbikes/{motorbike_id}/image"),
    ("post", "/api/v1/catalog-media/{vehicle_type}/{vehicle_id}/upload"),
}
PUBLIC_OPERATIONS = {
    ("get", "/health"),
    ("post", "/api/v1/auth/register"),
    ("post", "/api/v1/auth/login"),
    ("get", "/api/v1/cars"),
    ("get", "/api/v1/cars/{car_id_or_code}"),
    ("get", "/api/v1/motorbikes"),
    ("get", "/api/v1/motorbikes/{motorbike_id_or_code}"),
    ("get", "/api/v1/catalog-media/{vehicle_type}/{vehicle_id}"),
    ("get", "/api/v1/locations"),
    ("post", "/api/v1/tco/calculate"),
}
REQUIRED_PROTECTED = {
    ("get", "/api/v1/auth/me"),
    ("get", "/api/v1/quotes"),
    ("post", "/api/v1/quotes"),
    ("get", "/api/v1/bookings"),
    ("post", "/api/v1/bookings"),
    ("get", "/api/v1/conversations"),
    ("post", "/api/v1/conversations"),
}


@pytest.fixture
async def spec(client):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


def operations(spec):
    for path, items in spec["paths"].items():
        for method, operation in items.items():
            yield method, path, operation


def concrete_path(path: str) -> str:
    replacements = {"vehicle_type": "car"}
    return re.sub(r"\{(\w+)\}", lambda match: replacements.get(match.group(1), str(uuid.uuid4())), path)


async def test_required_rest_methods_are_published(spec):
    methods = {method for method, _, _ in operations(spec)}
    assert {"get", "post", "delete"} <= methods


async def test_bearer_security_scheme_is_declared(spec):
    schemes = spec["components"]["securitySchemes"]
    assert schemes["HTTPBearer"] == {**schemes["HTTPBearer"], "type": "http", "scheme": "bearer"}


async def test_security_declarations_match_the_access_policy(spec):
    declared = {(method, path): bool(op.get("security")) for method, path, op in operations(spec)}
    for key in REQUIRED_PROTECTED:
        assert declared[key], f"{key} must require authentication"
    for key, secured in declared.items():
        assert secured == (key not in PUBLIC_OPERATIONS), f"{key} security={secured}"


async def test_request_bodies_are_json_except_documented_uploads(spec):
    for method, path, operation in operations(spec):
        body = operation.get("requestBody")
        if body is None:
            continue
        content_types = set(body["content"])
        expected = {MULTIPART} if (method, path) in MULTIPART_ENDPOINTS else {JSON}
        assert content_types == expected, f"{method.upper()} {path}: {content_types}"
    published = {(method, path) for method, path, op in operations(spec) if op.get("requestBody")}
    assert MULTIPART_ENDPOINTS <= published


async def test_every_operation_documents_a_typed_success_response(spec):
    for method, path, operation in operations(spec):
        success = {code: value for code, value in operation["responses"].items() if code.startswith("2")}
        assert len(success) == 1, f"{method.upper()} {path} must document one success code"
        code, response = next(iter(success.items()))
        if code == "204":
            continue
        schema = response["content"][JSON]["schema"]
        assert schema, f"{method.upper()} {path} has an empty response schema"


async def test_protected_operations_document_401(spec):
    for method, path, operation in operations(spec):
        if operation.get("security"):
            assert "401" in operation["responses"], f"{method.upper()} {path} must document 401"


async def test_every_protected_get_and_post_rejects_missing_token(client, spec):
    checked = 0
    for method, path, operation in operations(spec):
        if method not in {"get", "post"} or not operation.get("security"):
            continue
        response = await client.request(method.upper(), concrete_path(path), json={})
        assert response.status_code == 401, f"{method.upper()} {path} -> {response.status_code}"
        assert response.headers.get("www-authenticate") == "Bearer"
        checked += 1
    assert checked >= len([key for key in REQUIRED_PROTECTED])


async def test_every_protected_operation_rejects_a_forged_token(client, spec):
    headers = {"Authorization": "Bearer not-a-real-token"}
    for method, path, operation in operations(spec):
        if not operation.get("security"):
            continue
        response = await client.request(method.upper(), concrete_path(path), json={}, headers=headers)
        assert response.status_code == 401, f"{method.upper()} {path} -> {response.status_code}"


async def test_runtime_status_codes_match_the_contract(client, customer_headers, admin_headers):
    assert (await client.get("/api/v1/auth/users", headers=customer_headers)).status_code == 403
    assert (await client.get(f"/api/v1/cars/{uuid.uuid4()}")).status_code == 404
    invalid = await client.post("/api/v1/bookings", headers=customer_headers, json={"vehicle_id": "not-a-uuid"})
    assert invalid.status_code == 422
    assert "detail" in invalid.json()
    missing = await client.delete(f"/api/v1/cars/{uuid.uuid4()}", headers=admin_headers)
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Không tìm thấy mẫu xe"}


async def test_chat_is_published_and_retired_endpoints_are_not(spec):
    paths = spec["paths"]
    assert "/api/v1/conversations" in paths
    assert "/api/v1/conversations/{conversation_id}/messages" in paths
    assert "/api/v1/chat" not in paths
    assert "/api/v1/status" not in paths
