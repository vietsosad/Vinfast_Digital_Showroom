async def test_locations_are_seeded_in_the_database(client):
    response = await client.get("/api/v1/locations")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["total"] == len(body["data"]) == 129
    first = body["data"][0]
    assert {"typeLabel", "coordinates", "openingHours", "chargingInfo"} <= first.keys()


async def test_locations_filters(client):
    hanoi = (await client.get("/api/v1/locations", params={"province": "Hà Nội"})).json()
    assert hanoi["total"] > 0 and all(item["province"] == "Hà Nội" for item in hanoi["data"])

    swap = (await client.get("/api/v1/locations", params={"demand_type": "battery_swap"})).json()
    assert swap["total"] > 0 and all("battery_swap" in item["types"] for item in swap["data"])

    everywhere = (await client.get("/api/v1/locations", params={"province": "Tất cả tỉnh thành"})).json()
    assert everywhere["total"] == 129


async def test_sync_is_admin_only_and_idempotent(client, staff_headers, admin_headers):
    assert (await client.post("/api/v1/locations/sync", headers=staff_headers)).status_code == 403
    first = await client.post("/api/v1/locations/sync", headers=admin_headers)
    second = await client.post("/api/v1/locations/sync", headers=admin_headers)
    assert first.status_code == second.status_code == 200
    assert second.json()["total_synced"] == 129
    assert (await client.get("/api/v1/locations")).json()["total"] == 129
