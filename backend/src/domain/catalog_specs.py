"""Pure transformations for catalog technical specifications.

Catalog rows keep their detailed specification in ``additional_specs`` using
the ``_legacy_source`` layout produced by the original VinFast import. Every
create/update re-derives that layout from the canonical columns so the two
never drift apart. These rules are framework-free and unit-testable.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


def format_car_legacy_additional_specs(car_id, model_name, version, range_km, list_price, seat_count, power_kw,
                                       torque_nm, battery_kwh, length_mm, width_mm, height_mm, wheelbase_mm,
                                       is_active, raw_specs: dict) -> dict:
    if not isinstance(raw_specs, dict):
        raw_specs = {}

    if "_legacy_source" in raw_specs and isinstance(raw_specs["_legacy_source"], dict):
        preserved = deepcopy(raw_specs)
        legacy = deepcopy(raw_specs["_legacy_source"])
        catalog = legacy.setdefault("catalog", {})
        specifications = legacy.setdefault("specifications", {})
        if not isinstance(catalog, dict):
            catalog = {}
            legacy["catalog"] = catalog
        if not isinstance(specifications, dict):
            specifications = {}
            legacy["specifications"] = specifications
        additional = specifications.setdefault("additional_specs", {})
        if not isinstance(additional, dict):
            additional = {}
            specifications["additional_specs"] = additional

        raw_model = model_name
        if version and raw_model and raw_model.endswith(version):
            raw_model = raw_model[:-len(version)].strip()

        catalog["car_id"] = str(car_id)
        catalog["model_name"] = raw_model
        specifications["car_id"] = str(car_id)
        if version is not None:
            specifications["version"] = version
        if range_km is not None:
            specifications["range_km"] = range_km
        if list_price is not None:
            specifications["list_price"] = list_price
        if seat_count is not None:
            specifications["seat_count"] = seat_count
        if power_kw is not None:
            specifications["motor_power_kw"] = power_kw
        if battery_kwh is not None:
            specifications["battery_capacity_kwh"] = battery_kwh
        if is_active is not None:
            specifications["is_active"] = is_active
        if length_mm is not None:
            additional["length_mm"] = length_mm
        if width_mm is not None:
            additional["width_mm"] = width_mm
        if height_mm is not None:
            additional["height_mm"] = height_mm
        if wheelbase_mm is not None:
            additional["wheelbase_mm"] = wheelbase_mm
        if torque_nm is not None:
            additional["motor_torque_nm"] = torque_nm

        preserved["_legacy_source"] = legacy
        return preserved

    raw_model = model_name or raw_specs.get("model_name")
    if version and raw_model and raw_model.endswith(version):
        raw_model = raw_model[:-len(version)].strip()

    body_type = raw_specs.get("body_type")
    model_year = raw_specs.get("model_year")
    payload_kg = raw_specs.get("payload_kg")
    maximum_speed_kmh = raw_specs.get("maximum_speed_kmh")
    cargo_capacity_liters = raw_specs.get("cargo_capacity_liters")
    charging_time_minutes = raw_specs.get("charging_time_minutes")
    fuel_type = raw_specs.get("fuel_type") or "Điện"

    safety_features = raw_specs.get("safety_features") if isinstance(raw_specs.get("safety_features"), dict) else {}
    driver_assistance_features = raw_specs.get("driver_assistance_features") if isinstance(raw_specs.get("driver_assistance_features"), dict) else {}
    exterior_features = raw_specs.get("exterior_features") if isinstance(raw_specs.get("exterior_features"), dict) else {}
    interior_features = raw_specs.get("interior_features") if isinstance(raw_specs.get("interior_features"), dict) else {}

    inner_add_specs = {
        "images": raw_specs.get("images") if isinstance(raw_specs.get("images"), list) else [],
        "length_mm": length_mm if length_mm is not None else raw_specs.get("length_mm"),
        "width_mm": width_mm if width_mm is not None else raw_specs.get("width_mm"),
        "height_mm": height_mm if height_mm is not None else raw_specs.get("height_mm"),
        "wheelbase_mm": wheelbase_mm if wheelbase_mm is not None else raw_specs.get("wheelbase_mm"),
        "motor_torque_nm": torque_nm if torque_nm is not None else raw_specs.get("motor_torque_nm"),
        "front_brake": raw_specs.get("front_brake"),
        "rear_brake": raw_specs.get("rear_brake"),
        "front_suspension": raw_specs.get("front_suspension"),
        "rear_suspension": raw_specs.get("rear_suspension"),
        "engine_type": raw_specs.get("engine_type"),
        "battery_type": raw_specs.get("battery_type"),
        "transmission": raw_specs.get("transmission"),
        "curb_weight_kg": raw_specs.get("curb_weight_kg"),
        "standard_charger": raw_specs.get("standard_charger"),
        "acceleration_0_50_seconds": raw_specs.get("acceleration_0_50_seconds"),
        "motor_power_hp": raw_specs.get("motor_power_hp"),
        "ground_clearance_mm": raw_specs.get("ground_clearance_mm"),
        "drivetrain": raw_specs.get("drivetrain"),
        "tires_wheels": raw_specs.get("tires_wheels"),
        "cargo_capacity_folded_liters": raw_specs.get("cargo_capacity_folded_liters"),
        "turning_diameter_m": raw_specs.get("turning_diameter_m"),
        "roof_load_capacity_kg": raw_specs.get("roof_load_capacity_kg"),
        "dc_charge_from_percent": raw_specs.get("dc_charge_from_percent"),
        "dc_charge_to_percent": raw_specs.get("dc_charge_to_percent"),
        "price_info_text": raw_specs.get("price_info_text"),
        "charging_info_text": raw_specs.get("charging_info_text"),
        "range_condition_text": raw_specs.get("range_condition_text"),
        "regenerative_braking": raw_specs.get("regenerative_braking"),
        "technical_specs_text": raw_specs.get("technical_specs_text"),
        "warranty_text": raw_specs.get("warranty_text"),
        "description_text": raw_specs.get("description_text") or raw_specs.get("description"),
        "colors": raw_specs.get("colors") if isinstance(raw_specs.get("colors"), list) else [],
        "safety_features": safety_features,
        "driver_assistance_features": driver_assistance_features,
        "exterior_features": exterior_features,
        "interior_features": interior_features,
    }

    root_spec_keys = {
        "car_id", "version", "range_km", "body_type", "fuel_type", "is_active",
        "list_price", "model_year", "payload_kg", "seat_count", "motor_power_kw",
        "maximum_speed_kmh", "battery_capacity_kwh", "cargo_capacity_liters",
        "charging_time_minutes", "additional_specs", "_legacy_source", "catalog", "specifications"
    }

    for k, v in raw_specs.items():
        if k not in inner_add_specs and k not in root_spec_keys:
            inner_add_specs[k] = v

    return {
        "_legacy_source": {
            "catalog": {
                "car_id": str(car_id),
                "model_name": raw_model
            },
            "specifications": {
                "car_id": str(car_id),
                "version": version or raw_specs.get("version"),
                "range_km": range_km if range_km is not None else raw_specs.get("range_km"),
                "body_type": body_type,
                "fuel_type": fuel_type,
                "is_active": is_active if is_active is not None else raw_specs.get("is_active"),
                "list_price": list_price if list_price is not None else raw_specs.get("list_price"),
                "model_year": model_year,
                "payload_kg": payload_kg,
                "seat_count": seat_count if seat_count is not None else raw_specs.get("seat_count"),
                "motor_power_kw": power_kw if power_kw is not None else raw_specs.get("motor_power_kw"),
                "maximum_speed_kmh": maximum_speed_kmh,
                "battery_capacity_kwh": battery_kwh if battery_kwh is not None else raw_specs.get("battery_capacity_kwh"),
                "cargo_capacity_liters": cargo_capacity_liters,
                "charging_time_minutes": charging_time_minutes,
                "additional_specs": inner_add_specs
            }
        }
    }



def format_motorbike_legacy_additional_specs(
    motorbike_id, model_name: str | None, version: str | None, range_km: float | None, list_price: int | None,
    length_mm: int | None, width_mm: int | None, height_mm: int | None, is_active: bool | None, raw_specs: dict,
    motor_type: str | None = None,
    battery_type: str | None = None,
    battery_quantity: int | None = None,
    battery_capacity_kwh: float | None = None,
    maximum_motor_power_w: float | None = None,
    maximum_speed_kmh: float | None = None,
    charging_time_minutes: int | None = None,
    description: str | None = None,
) -> dict:
    if not isinstance(raw_specs, dict):
        raw_specs = {}

    legacy_base = raw_specs.get("_legacy_source") if isinstance(raw_specs.get("_legacy_source"), dict) else None
    specs_base = legacy_base.get("specifications") if (legacy_base and isinstance(legacy_base.get("specifications"), dict)) else {}
    add_base = specs_base.get("additional_specs") if (specs_base and isinstance(specs_base.get("additional_specs"), dict)) else {}

    def get_val(key: str, arg_val: Any = None):
        if arg_val is not None:
            return arg_val
        if key in raw_specs and raw_specs[key] is not None:
            return raw_specs[key]
        if key in specs_base and specs_base[key] is not None:
            return specs_base[key]
        if key in add_base and add_base[key] is not None:
            return add_base[key]
        return None

    raw_model = model_name or (legacy_base.get("catalog", {}).get("model_name") if legacy_base else None) or raw_specs.get("model_name")

    specifications = {
        "motorbike_id": str(motorbike_id) if motorbike_id else None,
        "version": get_val("version", version),
        "range_km": get_val("range_km", range_km),
        "list_price": get_val("list_price", list_price),
        "is_active": is_active if is_active is not None else get_val("is_active"),
        "length_mm": get_val("length_mm", length_mm),
        "width_mm": get_val("width_mm", width_mm),
        "height_mm": get_val("height_mm", height_mm),
        "model_year": get_val("model_year"),
        "motor_type": get_val("motor_type", motor_type),
        "battery_type": get_val("battery_type", battery_type),
        "charger_type": get_val("charger_type"),
        "wet_weight_kg": get_val("wet_weight_kg"),
        "charger_power_w": get_val("charger_power_w"),
        "battery_quantity": get_val("battery_quantity", battery_quantity),
        "battery_voltage_v": get_val("battery_voltage_v"),
        "maximum_speed_kmh": get_val("maximum_speed_kmh", maximum_speed_kmh),
        "removable_battery": get_val("removable_battery"),
        "battery_capacity_ah": get_val("battery_capacity_ah"),
        "rated_motor_power_w": get_val("rated_motor_power_w"),
        "battery_capacity_kwh": get_val("battery_capacity_kwh", battery_capacity_kwh),
        "charging_time_minutes": get_val("charging_time_minutes", charging_time_minutes),
        "maximum_motor_power_w": get_val("maximum_motor_power_w", maximum_motor_power_w),
        "battery_swap_supported": get_val("battery_swap_supported"),
        "underseat_storage_liters": get_val("underseat_storage_liters"),
        "water_resistance_standard": get_val("water_resistance_standard"),
    }

    raw_light = get_val("lighting_features")
    if not isinstance(raw_light, dict):
        raw_light = {}
    lighting_features = {
        "headlight": get_val("headlight") or raw_light.get("headlight"),
        "tail_light": get_val("tail_light") or raw_light.get("tail_light"),
        "turn_signal": get_val("turn_signal") or raw_light.get("turn_signal"),
    }

    raw_tech = get_val("technology_features")
    if not isinstance(raw_tech, dict):
        raw_tech = {}
    # Preserve every catalog technology field. The previous formatter retained
    # only three keys, so an admin save could silently delete GPS, display,
    # Smartkey, Bluetooth and other verified features.
    technology_features = dict(raw_tech)
    for key in ("battery_swap", "smart_management", "license_requirement"):
        value = get_val(key)
        if value is not None:
            technology_features[key] = value

    smart_features = get_val("smart_features")
    if not isinstance(smart_features, dict):
        smart_features = None

    raw_colors = get_val("colors")
    colors_list = []
    if isinstance(raw_colors, list):
        colors_list = [c.strip() for c in raw_colors if isinstance(c, str) and c.strip()]
    elif isinstance(raw_colors, str) and raw_colors.strip():
        colors_list = [c.strip() for c in raw_colors.split(",") if c.strip()]

    images = get_val("images")
    if not isinstance(images, list):
        images = []
    source_refs = get_val("source_refs")
    if not isinstance(source_refs, list):
        source_refs = []

    additional_specs = {
        "colors": colors_list if colors_list else None,
        "images": images,
        "source_refs": source_refs,
        "rear_tire": get_val("rear_tire"),
        "front_tire": get_val("front_tire"),
        "rear_brake": get_val("rear_brake"),
        "front_brake": get_val("front_brake"),
        "warranty_text": get_val("warranty_text"),
        "price_info_text": get_val("price_info_text"),
        "rear_suspension": get_val("rear_suspension"),
        "battery_location": get_val("battery_location"),
        "description_text": description or get_val("description_text") or get_val("description"),
        "front_suspension": get_val("front_suspension"),
        "charging_info_text": get_val("charging_info_text"),
        "range_condition_text": get_val("range_condition_text"),
        "technical_specs_text": get_val("technical_specs_text"),
        "battery_capacity_text": get_val("battery_capacity_text"),
        "lighting_features": lighting_features,
        "technology_features": technology_features,
        "smart_features": smart_features,
    }

    def clean_dict(d: dict) -> dict:
        cleaned = {}
        for k, v in d.items():
            if v is None or (isinstance(v, str) and len(v.strip()) == 0):
                continue
            if isinstance(v, dict):
                child = clean_dict(v)
                if child:
                    cleaned[k] = child
            else:
                cleaned[k] = v
        return cleaned

    cleaned_specs = clean_dict(specifications)
    cleaned_add_specs = clean_dict(additional_specs)
    if cleaned_add_specs:
        cleaned_specs["additional_specs"] = cleaned_add_specs

    catalog = {
        "motorbike_id": str(motorbike_id) if motorbike_id else None,
        "model_name": raw_model
    }
    cleaned_catalog = clean_dict(catalog)

    return {
        "_legacy_source": {
            "catalog": cleaned_catalog,
            "specifications": cleaned_specs
        }
    }


def is_ebus(model_name: str | None, vehicle_line: str | None) -> bool:
    return bool(re.search(r"ebus", f"{model_name or ''} {vehicle_line or ''}", re.IGNORECASE))


def extract_top_level_colors(raw_specs: dict[str, Any]) -> list[Any] | None:
    """Read colors from an incoming payload while keeping one canonical field."""
    if "colors" in raw_specs:
        value = raw_specs["colors"]
    else:
        legacy = raw_specs.get("_legacy_source")
        specifications = legacy.get("specifications") if isinstance(legacy, dict) else None
        additional = specifications.get("additional_specs") if isinstance(specifications, dict) else None
        value = additional.get("colors") if isinstance(additional, dict) else None
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return None

