import uuid

from tests.helpers import register


async def test_crm_is_staff_only(client, customer_headers):
    assert (await client.get("/api/v1/customer-profiles", headers=customer_headers)).status_code == 403
    assert (await client.get(f"/api/v1/customer-profiles/{uuid.uuid4()}", headers=customer_headers)).status_code == 403


async def test_staff_searches_and_updates_profiles(client, staff_headers):
    customer = await register(client)
    results = await client.get("/api/v1/customer-profiles", headers=staff_headers, params={"search": customer["email"]})
    assert results.status_code == 200
    [profile] = results.json()
    assert profile["account"]["email"] == customer["email"]

    updated = await client.put(
        f"/api/v1/customer-profiles/{profile['profile_id']}",
        headers=staff_headers,
        json={"lead_score": "COLD", "customer_note": "  Gọi lại sau Tết  ", "all_interested_models": ["VF 6", "VF 6", " "]},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["lead_score"] == "COLD"
    assert body["customer_note"] == "Gọi lại sau Tết"
    assert body["all_interested_models"] == ["VF 6"]

    cleared = await client.put(
        f"/api/v1/customer-profiles/{profile['profile_id']}", headers=staff_headers, json={"customer_note": None}
    )
    assert cleared.json()["customer_note"] is None

    detail = await client.get(f"/api/v1/customer-profiles/{profile['profile_id']}", headers=staff_headers)
    assert detail.json()["lead_score"] == "COLD"


async def test_profile_enums_are_validated(client, staff_headers):
    customer = await register(client)
    profiles = (await client.get("/api/v1/customer-profiles", headers=staff_headers, params={"search": customer["email"]})).json()
    response = await client.put(
        f"/api/v1/customer-profiles/{profiles[0]['profile_id']}", headers=staff_headers, json={"lead_score": "BOILING"}
    )
    assert response.status_code == 422
    assert (await client.get("/api/v1/customer-profiles", headers=staff_headers, params={"lead_status": "X"})).status_code == 422


async def test_unknown_profile_is_404(client, staff_headers):
    assert (await client.get(f"/api/v1/customer-profiles/{uuid.uuid4()}", headers=staff_headers)).status_code == 404
