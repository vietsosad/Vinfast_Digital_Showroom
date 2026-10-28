import uuid
from datetime import date, timedelta

from tests.helpers import register

NEXT_WEEK = str(date.today() + timedelta(days=7))


async def book(client, headers, vehicle_id, **extra):
    return await client.post(
        "/api/v1/bookings",
        headers=headers,
        json={"vehicle_id": vehicle_id, "preferred_date": NEXT_WEEK, "preferred_time": "10:00", **extra},
    )


async def test_booking_is_owned_by_the_token_subject(client, customer_headers, car):
    response = await book(client, customer_headers, car["id"], customer_name="Giả mạo", customer_phone="0000000000")
    assert response.status_code == 201, response.text
    booking = response.json()
    me = (await client.get("/api/v1/auth/me", headers=customer_headers)).json()
    assert booking["user_id"] == me["id"]
    assert booking["customer_phone"] == me["phone"]
    assert booking["vehicle_name"] == car["model_name"]


async def test_reused_phone_number_does_not_leak_bookings(client, car):
    """Regression for the IDOR: bookings used to be matched to customers by phone number."""
    victim = await register(client)
    assert (await book(client, victim["headers"], car["id"])).status_code == 201

    # The victim changes number; the old number is now free and an attacker registers it.
    changed = await client.put("/api/v1/auth/me", headers=victim["headers"], json={"phone": "0987654321"})
    assert changed.status_code == 200
    attacker = await register(client, phone=victim["phone"])

    listing = await client.get("/api/v1/bookings", headers=attacker["headers"], params={"phone": victim["phone"]})
    assert listing.status_code == 200
    assert listing.json() == []
    assert len((await client.get("/api/v1/bookings", headers=victim["headers"])).json()) == 1


async def test_staff_sees_all_bookings_and_can_filter(client, customer_headers, staff_headers, car):
    other = await register(client)
    await book(client, customer_headers, car["id"])
    await book(client, other["headers"], car["id"])
    everything = (await client.get("/api/v1/bookings", headers=staff_headers)).json()
    assert len(everything) == 2
    filtered = (await client.get("/api/v1/bookings", headers=staff_headers, params={"phone": other["phone"]})).json()
    assert [item["customer_phone"] for item in filtered] == [other["phone"]]


async def test_booking_validation(client, customer_headers, car):
    past = await client.post(
        "/api/v1/bookings",
        headers=customer_headers,
        json={"vehicle_id": car["id"], "preferred_date": str(date.today() - timedelta(days=2))},
    )
    assert past.status_code == 422
    bad_time = await book(client, customer_headers, car["id"], preferred_time="25:00")
    assert bad_time.status_code == 422
    unknown_vehicle = await book(client, customer_headers, str(uuid.uuid4()))
    assert unknown_vehicle.status_code == 404


async def test_booking_status_transitions(client, customer_headers, staff_headers, car):
    booking = (await book(client, customer_headers, car["id"])).json()
    url = f"/api/v1/bookings/{booking['id']}"

    assert (await client.put(url, headers=customer_headers, json={"status": "confirmed"})).status_code == 403
    assert (await client.put(url, headers=staff_headers, json={"status": "completed"})).status_code == 409
    assert (await client.put(url, headers=staff_headers, json={"status": "confirmed"})).status_code == 200
    completed = await client.put(url, headers=staff_headers, json={"status": "completed", "notes": "Khách hài lòng"})
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert (await client.put(url, headers=staff_headers, json={"status": "cancelled"})).status_code == 409
    assert (await client.put(f"/api/v1/bookings/{uuid.uuid4()}", headers=staff_headers, json={"status": "confirmed"})).status_code == 404


async def test_booking_updates_crm_profile(client, car):
    customer = await register(client)
    await book(client, customer["headers"], car["id"])
    profile = (await client.get("/api/v1/customer-profiles/me", headers=customer["headers"])).json()
    assert profile["total_test_drives"] == 1
    assert profile["lead_score"] == "HOT"
    assert profile["lead_status"] == "TEST_DRIVEN"
