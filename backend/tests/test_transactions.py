"""A use case's writes commit together or not at all."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from src.infrastructure.database import SessionLocal
from src.infrastructure.orm import AccountRow, CustomerProfileRow, QuoteRow
from src.infrastructure.repositories.customer_profiles import SqlAlchemyCustomerProfileRepository
from src.main import app


@pytest_asyncio.fixture
async def tolerant_client():
    """Client that returns the 500 response instead of re-raising the server error."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


async def count(model) -> int:
    async with SessionLocal() as session:
        return await session.scalar(select(func.count()).select_from(model))


async def test_quote_is_rolled_back_when_crm_update_fails(tolerant_client, customer_headers, car, monkeypatch):
    async def broken_save(self, profile):
        raise RuntimeError("CRM store unavailable")

    monkeypatch.setattr(SqlAlchemyCustomerProfileRepository, "save", broken_save)
    quotes_before = await count(QuoteRow)

    response = await tolerant_client.post("/api/v1/quotes", headers=customer_headers, json={"vehicle_id": car["id"]})
    assert response.status_code == 500
    assert response.json() == {"detail": "Lỗi hệ thống không mong muốn"}

    assert await count(QuoteRow) == quotes_before


async def test_registration_does_not_leave_an_account_without_profile(tolerant_client, monkeypatch):
    async def broken_add(self, profile):
        raise RuntimeError("CRM store unavailable")

    monkeypatch.setattr(SqlAlchemyCustomerProfileRepository, "add", broken_add)
    accounts_before = await count(AccountRow)
    profiles_before = await count(CustomerProfileRow)

    response = await tolerant_client.post(
        "/api/v1/auth/register",
        json={"email": "atomic@example.com", "password": "Password123!", "full_name": "Nguyên Tử", "phone": "0966666666"},
    )
    assert response.status_code == 500

    assert await count(AccountRow) == accounts_before
    assert await count(CustomerProfileRow) == profiles_before
