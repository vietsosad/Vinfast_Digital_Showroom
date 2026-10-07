import uuid

import pytest


async def login(client, email: str, password: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_customer_and_staff_conversation_flow(client):
    customer_headers = await login(client, "customer@gmail.com", "123456")
    staff_headers = await login(client, "staff@vinfast.vn", "staff123")

    created = await client.post(
        "/api/v1/conversations",
        headers=customer_headers,
        json={"subject": "Đặt lịch lái thử VF 6"},
    )
    assert created.status_code == 201, created.text
    conversation_id = created.json()["conversation_id"]

    customer_message = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=customer_headers,
        json={"content": "Tôi muốn lái thử vào sáng thứ Bảy."},
    )
    assert customer_message.status_code == 201

    queue = await client.get("/api/v1/conversations", headers=staff_headers)
    assert queue.status_code == 200
    assert any(item["conversation_id"] == conversation_id for item in queue.json())

    unassigned_reply = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=staff_headers,
        json={"content": "Tin nhắn này phải bị chặn trước khi nhận hội thoại."},
    )
    assert unassigned_reply.status_code == 403

    assigned = await client.post(
        f"/api/v1/conversations/{conversation_id}/assign",
        headers=staff_headers,
    )
    assert assigned.status_code == 200
    assert assigned.json()["assigned_staff_id"] is not None

    staff_message = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=staff_headers,
        json={"content": "Chào anh/chị, em đã tiếp nhận yêu cầu."},
    )
    assert staff_message.status_code == 201

    history = await client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=customer_headers,
    )
    assert history.status_code == 200
    assert [message["sender_role"] for message in history.json()] == ["customer", "consultant"]

    closed = await client.post(
        f"/api/v1/conversations/{conversation_id}/close",
        headers=customer_headers,
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    after_close = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=customer_headers,
        json={"content": "Không thể gửi sau khi đóng."},
    )
    assert after_close.status_code == 422


@pytest.mark.asyncio
async def test_customer_cannot_read_another_customers_conversation(client):
    owner_headers = await login(client, "customer@gmail.com", "123456")
    created = await client.post(
        "/api/v1/conversations",
        headers=owner_headers,
        json={"subject": "Hỗ trợ báo giá VF 8"},
    )
    conversation_id = created.json()["conversation_id"]

    unique = uuid.uuid4().hex[:8]
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"customer-{unique}@example.com",
            "password": "Password123!",
            "full_name": "Khách hàng thứ hai",
            "phone": f"09{unique}",
            "role": "customer",
        },
    )
    assert registration.status_code == 201, registration.text
    other_headers = await login(client, f"customer-{unique}@example.com", "Password123!")

    response = await client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=other_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_customer_can_delete_own_conversation(client):
    headers = await login(client, "customer@gmail.com", "123456")
    created = await client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"subject": "Yêu cầu không còn cần hỗ trợ"},
    )
    conversation_id = created.json()["conversation_id"]

    deleted = await client.delete(f"/api/v1/conversations/{conversation_id}", headers=headers)
    assert deleted.status_code == 204

    history = await client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=headers)
    assert history.status_code == 404
