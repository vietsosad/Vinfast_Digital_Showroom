from src.application.tco import DISCLAIMER_TEXT


async def test_tco_endpoint_is_public_and_json(client):
    response = await client.post(
        "/api/v1/tco/calculate",
        json={
            "vehicle_type": "CAR",
            "model_id": "vf8-eco",
            "province_code": "HN",
            "battery_option": "RENTAL",
            "monthly_km_estimate": 1200,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model_id"] == "vf8-eco"
    assert data["disclaimer_text"] == DISCLAIMER_TEXT
    assert data["rolling_cost_breakdown"]["registration_fee_vnd"] == 0


async def test_tco_validates_input_ranges(client):
    response = await client.post("/api/v1/tco/calculate", json={"model_id": "vf5", "seat_count": 50})
    assert response.status_code == 422
