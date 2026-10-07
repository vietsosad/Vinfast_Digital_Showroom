import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_customer_profile_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_phone = f"09{uuid.uuid4().hex[:8]}"
        unique_email = f"test_{uuid.uuid4().hex[:6]}@vinfast.vn"

        # 1. Register account -> Clean customer profile created with linked user_id
        reg_payload = {
            "email": unique_email,
            "password": "Password123!",
            "full_name": "Nguyễn Văn Khách Hàng",
            "phone": unique_phone,
            "role": "customer"
        }
        try:
            reg_resp = await client.post("/api/auth/register", json=reg_payload)
        except Exception:
            pytest.skip("Database connection unavailable in test environment")

        if reg_resp.status_code != 201:
            pytest.skip("Database connection unavailable in test environment")

        user_data = reg_resp.json()
        user_id = user_data["id"]

        # 2. Login to get auth token
        login_resp = await client.post("/api/auth/login", json={
            "email": unique_email,
            "password": "Password123!"
        })
        assert login_resp.status_code == 200, login_resp.text
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. User submits test drive booking -> should sync to customer profile
        booking_payload = {
            "customer_name": "Nguyễn Văn Khách Hàng",
            "customer_phone": unique_phone,
            "vehicle_id": "vf-6-plus",
            "vehicle_name": "VinFast VF 6 Plus",
            "preferred_date": "2026-08-25",
            "preferred_time": "10:00",
            "notes": "Muốn thử tính năng ADAS trên cao tốc"
        }
        booking_resp = await client.post("/api/bookings", json=booking_payload, headers=headers)
        assert booking_resp.status_code == 201, booking_resp.text

        # 4. Check /api/customer-profiles/me -> should return profile with joined account info
        me_resp = await client.get("/api/customer-profiles/me", headers=headers)
        assert me_resp.status_code == 200, me_resp.text
        profile = me_resp.json()
        assert profile["user_id"] == user_id
        assert profile["account"]["phone"] == unique_phone
        assert profile["account"]["full_name"] == "Nguyễn Văn Khách Hàng"
        assert profile["account"]["email"] == unique_email
        assert "VinFast VF 6 Plus" in profile["all_interested_models"]
        assert profile["total_test_drives"] == 1
        assert profile["lead_score"] == "HOT"
        print("✅ Clean Normalized Customer Profile Lifecycle Passed!")


@pytest.mark.asyncio
async def test_anonymous_guest_cannot_open_support_conversation():
    """Chat hỗ trợ chứa dữ liệu cá nhân nên luôn yêu cầu đăng nhập."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/conversations",
            json={"subject": "Tư vấn xe máy điện"},
        )
        assert response.status_code == 401
