import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.main import app
from tests.helpers import login, register


async def open_conversation(client, headers, subject="Đặt lịch lái thử VF 6"):
    response = await client.post("/api/v1/conversations", headers=headers, json={"subject": subject})
    assert response.status_code == 201, response.text
    return response.json()["conversation_id"]


async def test_customer_and_staff_conversation_flow(client, customer_headers, staff_headers):
    conversation_id = await open_conversation(client, customer_headers)
    url = f"/api/v1/conversations/{conversation_id}"

    customer_message = await client.post(f"{url}/messages", headers=customer_headers, json={"content": "Tôi muốn lái thử vào sáng thứ Bảy."})
    assert customer_message.status_code == 201

    queue = await client.get("/api/v1/conversations", headers=staff_headers)
    assert any(item["conversation_id"] == conversation_id for item in queue.json())

    unassigned = await client.post(f"{url}/messages", headers=staff_headers, json={"content": "Chưa nhận hội thoại."})
    assert unassigned.status_code == 403

    assigned = await client.post(f"{url}/assign", headers=staff_headers)
    assert assigned.status_code == 200
    assert assigned.json()["assigned_staff_id"] is not None

    staff_message = await client.post(f"{url}/messages", headers=staff_headers, json={"content": "Em đã tiếp nhận yêu cầu."})
    assert staff_message.status_code == 201

    history = await client.get(f"{url}/messages", headers=customer_headers)
    assert [message["sender_role"] for message in history.json()] == ["customer", "consultant"]

    closed = await client.post(f"{url}/close", headers=customer_headers)
    assert closed.json()["status"] == "closed"
    after_close = await client.post(f"{url}/messages", headers=customer_headers, json={"content": "Không thể gửi."})
    assert after_close.status_code == 422


async def test_staff_cannot_open_conversations(client, staff_headers):
    response = await client.post("/api/v1/conversations", headers=staff_headers, json={"subject": "Nhân viên mở"})
    assert response.status_code == 403


async def test_customer_cannot_read_another_customers_conversation(client, customer_headers):
    conversation_id = await open_conversation(client, customer_headers, "Hỗ trợ báo giá VF 8")
    other = await register(client)
    response = await client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=other["headers"])
    assert response.status_code == 403
    listing = await client.get("/api/v1/conversations", headers=other["headers"])
    assert listing.json() == []


async def test_customer_can_delete_own_conversation(client, customer_headers):
    conversation_id = await open_conversation(client, customer_headers, "Không còn cần hỗ trợ")
    await client.post(f"/api/v1/conversations/{conversation_id}/messages", headers=customer_headers, json={"content": "Xin chào"})
    deleted = await client.delete(f"/api/v1/conversations/{conversation_id}", headers=customer_headers)
    assert deleted.status_code == 204
    history = await client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=customer_headers)
    assert history.status_code == 404


async def test_websocket_rejects_invalid_token_and_foreign_conversation(client, customer_headers):
    conversation_id = await open_conversation(client, customer_headers)
    other = await register(client)
    other_token = other["headers"]["Authorization"].removeprefix("Bearer ")

    with TestClient(app) as sync_client:
        with pytest.raises(WebSocketDisconnect) as invalid:
            with sync_client.websocket_connect(f"/api/v1/conversations/{conversation_id}/ws?token=forged"):
                pass
        assert invalid.value.code == 4401

        with pytest.raises(WebSocketDisconnect) as foreign:
            with sync_client.websocket_connect(f"/api/v1/conversations/{conversation_id}/ws?token={other_token}"):
                pass
        assert foreign.value.code == 4403


async def test_websocket_delivers_persisted_messages(client, customer_headers, staff_headers):
    conversation_id = await open_conversation(client, customer_headers)
    await client.post(f"/api/v1/conversations/{conversation_id}/assign", headers=staff_headers)
    customer_token = customer_headers["Authorization"].removeprefix("Bearer ")

    with TestClient(app) as sync_client:
        with sync_client.websocket_connect(f"/api/v1/conversations/{conversation_id}/ws?token={customer_token}") as socket:
            socket.send_json({"content": "  Gửi qua WebSocket  "})
            event = socket.receive_json()
            assert event["type"] == "message"
            assert event["message"]["content"] == "Gửi qua WebSocket"

            socket.send_json({"content": "   "})
            assert socket.receive_json()["type"] == "error"

            staff = sync_client.post(
                f"/api/v1/conversations/{conversation_id}/messages",
                headers=staff_headers,
                json={"content": "Nhân viên trả lời qua REST"},
            )
            assert staff.status_code == 201
            pushed = socket.receive_json()
            assert pushed["message"]["sender_role"] == "consultant"

            # Closing over REST must be visible to the long-lived socket session.
            closed = sync_client.post(f"/api/v1/conversations/{conversation_id}/close", headers=staff_headers)
            assert closed.status_code == 200
            assert socket.receive_json() == {"type": "conversation_updated", "status": "closed"}
            socket.send_json({"content": "Gửi sau khi đã đóng"})
            assert socket.receive_json()["type"] == "error"

    history = await client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=await login(client, "customer@gmail.com", "123456"))
    assert [item["content"] for item in history.json()] == ["Gửi qua WebSocket", "Nhân viên trả lời qua REST"]
