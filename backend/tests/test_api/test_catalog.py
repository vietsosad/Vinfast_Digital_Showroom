import uuid
from pathlib import Path

from src.config import get_settings

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


async def test_seeded_catalog_is_public_and_sorted_by_price(client):
    cars = (await client.get("/api/v1/cars")).json()
    motorbikes = (await client.get("/api/v1/motorbikes")).json()
    assert len(cars) == 21 and len(motorbikes) == 18
    prices = [car["list_price"] for car in cars]
    assert prices == sorted(prices)


async def test_ebus_has_no_color_catalog(client):
    cars = (await client.get("/api/v1/cars", params={"category": "Bus"})).json()
    assert cars and all(car["colors"] is None for car in cars)


async def test_car_lookup_by_id_and_by_code(client, car):
    by_id = await client.get(f"/api/v1/cars/{car['id']}")
    assert by_id.status_code == 200
    by_code = await client.get(f"/api/v1/cars/{car['vehicle_line']}")
    assert by_code.status_code == 200
    assert by_code.json()["vehicle_line"].lower() == car["vehicle_line"].lower()
    assert (await client.get("/api/v1/cars/does-not-exist")).status_code == 404


async def test_staff_creates_updates_and_admin_deletes_car_with_json(client, staff_headers, admin_headers):
    created = await client.post(
        "/api/v1/cars",
        headers=staff_headers,
        json={
            "model_name": "VinFast Test Plus",
            "version": "Plus",
            "list_price": 500_000_000,
            "range_km": 400,
            "additional_specs": {"colors": ["Đỏ", "Trắng"], "body_type": "SUV"},
        },
    )
    assert created.status_code == 201, created.text
    car = created.json()
    assert car["vehicle_line"] == "Test Plus"
    assert car["colors"] == ["Đỏ", "Trắng"]
    assert car["additional_specs"]["_legacy_source"]["specifications"]["body_type"] == "SUV"

    updated = await client.put(f"/api/v1/cars/{car['id']}", headers=staff_headers, json={"range_km": 450})
    assert updated.status_code == 200
    assert updated.json()["range_km"] == 450
    assert updated.json()["model_name"] == "VinFast Test Plus"
    assert updated.json()["additional_specs"]["_legacy_source"]["specifications"]["range_km"] == 450

    assert (await client.delete(f"/api/v1/cars/{car['id']}", headers=staff_headers)).status_code == 403
    deleted = await client.delete(f"/api/v1/cars/{car['id']}", headers=admin_headers)
    assert deleted.status_code == 200
    assert (await client.get(f"/api/v1/cars/{car['id']}")).status_code == 404


async def test_catalog_writes_reject_customers_and_invalid_payloads(client, customer_headers, staff_headers):
    body = {"model_name": "VinFast X", "list_price": 1}
    assert (await client.post("/api/v1/cars", headers=customer_headers, json=body)).status_code == 403
    negative = await client.post("/api/v1/cars", headers=staff_headers, json={"model_name": "VinFast X", "list_price": -1})
    assert negative.status_code == 422
    form = await client.post("/api/v1/cars", headers=staff_headers, data={"model_name": "VinFast X"})
    assert form.status_code == 422


async def test_motorbike_crud_round_trip(client, staff_headers, admin_headers):
    created = await client.post(
        "/api/v1/motorbikes",
        headers=staff_headers,
        json={
            "model_name": "VinFast Test Bike",
            "list_price": 30_000_000,
            "maximum_power_w": 2_000,
            "description": "Xe thử nghiệm",
            "additional_specs": {"front_brake": "Đĩa", "colors": ["Đen"]},
        },
    )
    assert created.status_code == 201, created.text
    bike = created.json()
    assert bike["front_brake"] == "Đĩa"
    assert bike["colors"] == ["Đen"]
    assert bike["battery_quantity"] == 1

    updated = await client.put(f"/api/v1/motorbikes/{bike['id']}", headers=staff_headers, json={"is_active": False})
    assert updated.json()["is_active"] is False
    assert (await client.delete(f"/api/v1/motorbikes/{bike['id']}", headers=admin_headers)).status_code == 200


async def test_car_image_upload_validates_signature_and_stores_file(client, staff_headers, car):
    fake = await client.post(
        f"/api/v1/cars/{car['id']}/image",
        headers=staff_headers,
        files={"image": ("evil.png", b"<?php echo 'hi'; ?>", "image/png")},
    )
    assert fake.status_code == 422

    mismatched = await client.post(
        f"/api/v1/cars/{car['id']}/image",
        headers=staff_headers,
        files={"image": ("photo.jpg", PNG_BYTES, "image/jpeg")},
    )
    assert mismatched.status_code == 422

    uploaded = await client.post(
        f"/api/v1/cars/{car['id']}/image",
        headers=staff_headers,
        files={"image": ("hero shot.png", PNG_BYTES, "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    url = uploaded.json()["image_url"]
    assert url.startswith("/static/uploads/cars/hero-shot-") and url.endswith(".png")
    stored = Path(get_settings().static_dir) / url.removeprefix("/static/")
    assert stored.read_bytes() == PNG_BYTES


async def test_oversized_upload_is_rejected_with_413(client, staff_headers, car):
    too_big = PNG_BYTES + b"\x00" * get_settings().max_upload_bytes
    response = await client.post(
        f"/api/v1/cars/{car['id']}/image",
        headers=staff_headers,
        files={"image": ("big.png", too_big, "image/png")},
    )
    assert response.status_code == 413


async def test_image_upload_for_unknown_vehicle_is_404(client, staff_headers):
    response = await client.post(
        f"/api/v1/motorbikes/{uuid.uuid4()}/image",
        headers=staff_headers,
        files={"image": ("a.png", PNG_BYTES, "image/png")},
    )
    assert response.status_code == 404
