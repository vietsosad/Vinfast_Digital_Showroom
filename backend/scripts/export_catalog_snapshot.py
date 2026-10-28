"""Export the frontend's bundled vehicle list into the reviewable seed dataset.

The backend never reads frontend sources at runtime. Run this script only when
the reference catalog changes, review the JSON diff, and commit it:

    python scripts/export_catalog_snapshot.py

The application seeds an empty database from data/catalog/vehicles.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
FRONTEND_CATALOG = REPOSITORY_ROOT / "frontend" / "src" / "data" / "vehicles.ts"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "data" / "catalog" / "vehicles.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=FRONTEND_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_frontend_catalog(path: Path = FRONTEND_CATALOG) -> list[dict[str, Any]]:
    source = path.read_text(encoding="utf-8")
    marker = "export const vehicles: Vehicle[] = "
    start = source.index(marker) + len(marker)
    end = source.index(";\n\nexport const heroSlides", start)
    payload = json.loads(source[start:end])
    if not isinstance(payload, list):
        raise ValueError("Frontend vehicle catalog must be a JSON array")
    return payload


def first_value(*values: Any) -> Any:
    return next((value for value in values if value is not None), None)


def car_values(vehicle: dict[str, Any]) -> dict[str, Any]:
    raw = vehicle.get("rawSpecs") or {}
    legacy = raw.get("additional_specs", {}).get("_legacy_source", {}).get("specifications", {})
    legacy_details = legacy.get("additional_specs") or {}
    additional_specs = raw.get("additional_specs") or raw.get("specs") or {}
    colors = first_value(raw.get("colors"), vehicle.get("colors"))
    return {
        "car_id": raw.get("car_id") or raw.get("id") or vehicle["id"],
        "model_name": raw.get("model_name") or raw.get("name") or vehicle["name"],
        "vehicle_line": raw.get("vehicle_line") or raw.get("code") or vehicle["code"],
        "version": raw.get("version"),
        "category": raw.get("category") or "Personal",
        "image_url": raw.get("image_url") or vehicle.get("image"),
        "colors": colors,
        "list_price": int(first_value(raw.get("list_price"), raw.get("base_price"), vehicle.get("basePrice"), 0)),
        "seat_count": first_value(raw.get("seat_count"), legacy.get("seat_count"), vehicle.get("seats")),
        "length_mm": first_value(raw.get("length_mm"), legacy_details.get("length_mm")),
        "width_mm": first_value(raw.get("width_mm"), legacy_details.get("width_mm")),
        "height_mm": first_value(raw.get("height_mm"), legacy_details.get("height_mm")),
        "wheelbase_mm": first_value(raw.get("wheelbase_mm"), legacy_details.get("wheelbase_mm")),
        "range_km": first_value(raw.get("range_km"), legacy.get("range_km"), vehicle.get("range")),
        "maximum_power_kw": first_value(raw.get("maximum_power_kw"), legacy.get("motor_power_kw")),
        "maximum_torque_nm": first_value(raw.get("maximum_torque_nm"), legacy_details.get("motor_torque_nm")),
        "usable_battery_capacity": first_value(
            raw.get("usable_battery_capacity"), legacy.get("battery_capacity_kwh")
        ),
        "additional_specs": additional_specs,
        "is_active": bool(first_value(raw.get("is_active"), raw.get("is_available"), True)),
    }


def motorbike_values(vehicle: dict[str, Any]) -> dict[str, Any]:
    raw = vehicle.get("rawSpecs") or {}
    additional_specs = raw.get("additional_specs") or raw.get("specs") or {}
    legacy = additional_specs.get("_legacy_source", {}).get("specifications", {})
    details = legacy.get("additional_specs") or {}
    return {
        "motorbike_id": raw.get("motorbike_id") or raw.get("id") or vehicle["id"],
        "model_name": raw.get("model_name") or raw.get("name") or vehicle["name"],
        "vehicle_line": raw.get("vehicle_line") or raw.get("code") or vehicle["code"],
        "version": raw.get("version"),
        "category": raw.get("category") or "motorbike",
        "image_url": raw.get("image_url") or vehicle.get("image"),
        "colors": first_value(raw.get("colors"), vehicle.get("colors"), []),
        "list_price": int(first_value(raw.get("list_price"), raw.get("base_price"), vehicle.get("basePrice"), 0)),
        "range_km": first_value(raw.get("range_km"), legacy.get("range_km"), vehicle.get("range")),
        "charging_time_minutes": first_value(raw.get("charging_time_minutes"), legacy.get("charging_time_minutes")),
        "battery_type": first_value(raw.get("battery_type"), legacy.get("battery_type")),
        "battery_quantity": first_value(raw.get("battery_quantity"), legacy.get("battery_quantity")),
        "battery_capacity_kwh": first_value(raw.get("battery_capacity_kwh"), legacy.get("battery_capacity_kwh")),
        "motor_type": first_value(raw.get("motor_type"), legacy.get("motor_type")),
        "maximum_power_w": first_value(
            raw.get("maximum_power_w"), raw.get("maximum_motor_power_w"), legacy.get("maximum_motor_power_w")
        ),
        "maximum_speed_kmh": first_value(raw.get("maximum_speed_kmh"), legacy.get("maximum_speed_kmh"), vehicle.get("topSpeed")),
        "weight_kg": first_value(raw.get("weight_kg"), legacy.get("wet_weight_kg")),
        "length_mm": first_value(raw.get("length_mm"), legacy.get("length_mm")),
        "width_mm": first_value(raw.get("width_mm"), legacy.get("width_mm")),
        "height_mm": first_value(raw.get("height_mm"), legacy.get("height_mm")),
        "front_brake": first_value(raw.get("front_brake"), details.get("front_brake")),
        "rear_brake": first_value(raw.get("rear_brake"), details.get("rear_brake")),
        "front_suspension": first_value(raw.get("front_suspension"), details.get("front_suspension")),
        "rear_suspension": first_value(raw.get("rear_suspension"), details.get("rear_suspension")),
        "additional_specs": additional_specs,
        "is_active": bool(first_value(raw.get("is_active"), raw.get("is_available"), True)),
    }


def build_snapshot(vehicles: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    snapshot: dict[str, list[dict[str, Any]]] = {"cars": [], "motorbikes": []}
    for vehicle in vehicles:
        raw = vehicle.get("rawSpecs") or {}
        if vehicle.get("category") == "scooter" or raw.get("motorbike_id"):
            snapshot["motorbikes"].append(motorbike_values(vehicle))
        else:
            snapshot["cars"].append(car_values(vehicle))
    for group in snapshot.values():
        for row in group:
            row.update({key: str(value) for key, value in row.items() if key.endswith("_id")})
    return snapshot


def main() -> None:
    args = parse_args()
    snapshot = build_snapshot(load_frontend_catalog(args.source))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(snapshot['cars'])} cars and {len(snapshot['motorbikes'])} motorbikes to {args.output}")


if __name__ == "__main__":
    main()
