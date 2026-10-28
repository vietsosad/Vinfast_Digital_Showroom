import uuid

from tests.helpers import register


async def test_quote_name_and_price_come_from_catalog_not_client(client, customer_headers, car):
    response = await client.post(
        "/api/v1/quotes",
        headers=customer_headers,
        json={
            "vehicle_id": car["id"],
            "request_note": "Muốn nhận giá lăn bánh",
            # Attempted tampering: these fields must be ignored.
            "vehicle_name": "Xe giá rẻ",
            "base_price": 1,
            "final_price": 1,
            "customer_name": "Người khác",
            "user_id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 201, response.text
    quote = response.json()
    assert quote["vehicle_name"] == car["model_name"]
    assert quote["base_price"] == car["list_price"]
    assert quote["final_price"] == car["list_price"]
    assert quote["discount"] == 0
    assert quote["customer_name"] == "Khách hàng Demo"
    assert quote["status"] == "pending"


async def test_quote_for_unknown_or_inactive_vehicle_is_rejected(client, customer_headers, staff_headers, car):
    missing = await client.post("/api/v1/quotes", headers=customer_headers, json={"vehicle_id": str(uuid.uuid4())})
    assert missing.status_code == 404

    await client.put(f"/api/v1/cars/{car['id']}", headers=staff_headers, json={"is_active": False})
    inactive = await client.post("/api/v1/quotes", headers=customer_headers, json={"vehicle_id": car["id"]})
    assert inactive.status_code == 422


async def test_customers_only_see_their_own_quotes_even_with_filters(client, customer_headers, car):
    other = await register(client)
    mine = (await client.post("/api/v1/quotes", headers=customer_headers, json={"vehicle_id": car["id"]})).json()
    theirs = (await client.post("/api/v1/quotes", headers=other["headers"], json={"vehicle_id": car["id"]})).json()

    listing = await client.get(
        "/api/v1/quotes", headers=other["headers"], params={"user_id": mine["user_id"], "phone": mine["customer_phone"]}
    )
    assert listing.status_code == 200
    assert [quote["id"] for quote in listing.json()] == [theirs["id"]]


async def test_staff_review_applies_discount_and_enforces_transitions(client, customer_headers, staff_headers, car):
    quote = (await client.post("/api/v1/quotes", headers=customer_headers, json={"vehicle_id": car["id"]})).json()

    assert (await client.put(f"/api/v1/quotes/{quote['id']}", headers=customer_headers, json={"status": "approved"})).status_code == 403

    too_much = await client.put(
        f"/api/v1/quotes/{quote['id']}",
        headers=staff_headers,
        json={"status": "approved", "discount": car["list_price"] + 1},
    )
    assert too_much.status_code == 422

    approved = await client.put(
        f"/api/v1/quotes/{quote['id']}",
        headers=staff_headers,
        json={"status": "approved", "discount": 10_000_000, "notes": "Ưu đãi tháng này"},
    )
    assert approved.status_code == 200
    body = approved.json()
    assert body["final_price"] == car["list_price"] - 10_000_000
    assert body["notes"] == "Ưu đãi tháng này"

    back_to_pending = await client.put(f"/api/v1/quotes/{quote['id']}", headers=staff_headers, json={"status": "pending"})
    assert back_to_pending.status_code == 409

    unknown_status = await client.put(f"/api/v1/quotes/{quote['id']}", headers=staff_headers, json={"status": "paid"})
    assert unknown_status.status_code == 422


async def test_quote_updates_crm_profile(client, staff_headers, car):
    customer = await register(client)
    await client.post("/api/v1/quotes", headers=customer["headers"], json={"vehicle_id": car["id"]})
    profile = (await client.get("/api/v1/customer-profiles/me", headers=customer["headers"])).json()
    assert profile["total_quotes"] == 1
    assert profile["lead_status"] == "QUOTED"
    assert car["model_name"] in profile["all_interested_models"]


async def test_staff_can_quote_a_negotiated_on_the_road_total(client, customer_headers, staff_headers, car):
    quote = (await client.post("/api/v1/quotes", headers=customer_headers, json={"vehicle_id": car["id"]})).json()
    on_the_road = car["list_price"] + 22_000_000 - 5_000_000
    response = await client.put(
        f"/api/v1/quotes/{quote['id']}",
        headers=staff_headers,
        # base_price from a client is ignored; only staff-set totals are stored.
        json={"status": "approved", "discount": 5_000_000, "final_price": on_the_road, "base_price": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["base_price"] == car["list_price"]
    assert body["discount"] == 5_000_000
    assert body["final_price"] == on_the_road
    assert (await client.put(f"/api/v1/quotes/{quote['id']}", headers=staff_headers, json={"status": "approved", "final_price": -1})).status_code == 422
