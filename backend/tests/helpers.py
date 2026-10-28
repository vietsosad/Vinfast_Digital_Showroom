"""HTTP helpers shared by API tests."""

import uuid

from httpx import AsyncClient


async def login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def register(client: AsyncClient, *, phone: str | None = None, password: str = "Password123!") -> dict:
    """Register a unique customer and return its user payload plus auth headers."""
    unique = uuid.uuid4().hex[:8]
    email = f"customer-{unique}@example.com"
    payload = {
        "email": email,
        "password": password,
        "full_name": f"Khách hàng {unique}",
        "phone": phone or f"09{int(unique, 16) % 10**8:08d}",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return {"user": response.json(), "headers": await login(client, email, password), **payload}
