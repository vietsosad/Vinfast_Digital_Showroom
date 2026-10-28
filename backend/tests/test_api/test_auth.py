import uuid
from datetime import date, timedelta

from tests.helpers import login, register


async def test_register_creates_customer_with_crm_profile(client):
    customer = await register(client)
    assert customer["user"]["role"] == "customer"
    profile = await client.get("/api/v1/customer-profiles/me", headers=customer["headers"])
    assert profile.status_code == 200
    assert profile.json()["user_id"] == customer["user"]["id"]


async def test_public_registration_cannot_choose_a_privileged_role(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "escalate@example.com",
            "password": "Password123!",
            "full_name": "Kẻ leo thang",
            "phone": "0911111111",
            "role": "admin",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "customer"


async def test_duplicate_email_is_rejected(client):
    first = await register(client)
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": first["email"].upper(), "password": "Password123!", "full_name": "Trùng", "phone": "0922222222"},
    )
    assert response.status_code == 409


async def test_duplicate_phone_is_rejected_on_register_and_profile_update(client):
    first = await register(client, phone="0933333333")
    duplicate = await client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "Password123!", "full_name": "Trùng SĐT", "phone": "0933 333 333"},
    )
    assert duplicate.status_code == 409

    second = await register(client)
    steal = await client.put("/api/v1/auth/me", headers=second["headers"], json={"phone": first["phone"]})
    assert steal.status_code == 409


async def test_login_rejects_wrong_password(client):
    response = await client.post("/api/v1/auth/login", json={"email": "customer@gmail.com", "password": "wrong-pass"})
    assert response.status_code == 401


async def test_me_returns_the_token_owner(client, customer_headers):
    response = await client.get("/api/v1/auth/me", headers=customer_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "customer@gmail.com"


async def test_customer_cannot_escalate_role_or_reactivate(client):
    customer = await register(client)
    user_id = customer["user"]["id"]
    response = await client.put(f"/api/v1/auth/users/{user_id}", headers=customer["headers"], json={"role": "admin"})
    assert response.status_code == 403
    me = await client.get("/api/v1/auth/me", headers=customer["headers"])
    assert me.json()["role"] == "customer"


async def test_customer_cannot_edit_another_account(client, customer_headers):
    other = await register(client)
    response = await client.put(
        f"/api/v1/auth/users/{other['user']['id']}", headers=customer_headers, json={"full_name": "Bị sửa trộm"}
    )
    assert response.status_code == 403


async def test_admin_only_endpoints_reject_staff_and_customers(client, customer_headers, staff_headers):
    for headers in (customer_headers, staff_headers):
        assert (await client.get("/api/v1/auth/users", headers=headers)).status_code == 403
        response = await client.post(
            "/api/v1/auth/create-staff",
            headers=headers,
            json={"email": "x@example.com", "password": "Password123!", "full_name": "X", "phone": "0944444444"},
        )
        assert response.status_code == 403


async def test_admin_creates_staff_with_valid_role_only(client, admin_headers):
    payload = {"email": "new-staff@vinfast.vn", "password": "Password123!", "full_name": "NV mới", "phone": "0955555555"}
    invalid = await client.post("/api/v1/auth/create-staff", headers=admin_headers, json={**payload, "role": "root"})
    assert invalid.status_code == 422
    created = await client.post("/api/v1/auth/create-staff", headers=admin_headers, json=payload)
    assert created.status_code == 201
    assert created.json()["role"] == "consultant"


async def test_deactivated_account_cannot_login_and_its_token_stops_working(client, admin_headers):
    customer = await register(client)
    response = await client.put(
        f"/api/v1/auth/users/{customer['user']['id']}", headers=admin_headers, json={"is_active": False}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    assert (await client.get("/api/v1/auth/me", headers=customer["headers"])).status_code == 401
    login_attempt = await client.post(
        "/api/v1/auth/login", json={"email": customer["email"], "password": customer["password"]}
    )
    assert login_attempt.status_code == 403


async def test_admin_cannot_demote_or_delete_self(client, admin_headers):
    me = (await client.get("/api/v1/auth/me", headers=admin_headers)).json()
    demote = await client.put(f"/api/v1/auth/users/{me['id']}", headers=admin_headers, json={"role": "customer"})
    assert demote.status_code == 409
    delete = await client.delete(f"/api/v1/auth/users/{me['id']}", headers=admin_headers)
    assert delete.status_code == 409


async def test_admin_deletes_account_and_its_owned_data(client, admin_headers, car):
    customer = await register(client)
    booking = await client.post(
        "/api/v1/bookings",
        headers=customer["headers"],
        json={"vehicle_id": car["id"], "preferred_date": str(date.today() + timedelta(days=7))},
    )
    assert booking.status_code == 201
    conversation = await client.post(
        "/api/v1/conversations", headers=customer["headers"], json={"subject": "Cần hỗ trợ trước khi xóa"}
    )
    assert conversation.status_code == 201

    deleted = await client.delete(f"/api/v1/auth/users/{customer['user']['id']}", headers=admin_headers)
    assert deleted.status_code == 200
    assert (await client.get("/api/v1/auth/me", headers=customer["headers"])).status_code == 401
    staff_view = await client.get("/api/v1/bookings", headers=admin_headers)
    orphaned = next(item for item in staff_view.json() if item["id"] == booking.json()["id"])
    assert orphaned["user_id"] is None
    missing = await client.delete(f"/api/v1/auth/users/{uuid.uuid4()}", headers=admin_headers)
    assert missing.status_code == 404


async def test_password_change_takes_effect(client):
    customer = await register(client)
    response = await client.put("/api/v1/auth/me", headers=customer["headers"], json={"password": "NewPassword456!"})
    assert response.status_code == 200
    await login(client, customer["email"], "NewPassword456!")


async def test_admin_edit_form_with_blank_password_keeps_the_password(client, admin_headers):
    customer = await register(client)
    response = await client.put(
        f"/api/v1/auth/users/{customer['user']['id']}",
        headers=admin_headers,
        json={"full_name": "Tên mới", "phone": customer["phone"], "role": "customer", "password": ""},
    )
    assert response.status_code == 200, response.text
    assert response.json()["full_name"] == "Tên mới"
    await login(client, customer["email"], customer["password"])
