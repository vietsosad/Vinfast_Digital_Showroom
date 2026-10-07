import json
import os
import re
import uuid
from copy import deepcopy
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.domain import Account, CarCatalog
from src.models.schemas import CarResponse
from src.services.database import get_db
from src.services.security import require_roles

router = APIRouter()

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
UPLOAD_DIR = os.path.join("/tmp", "uploads", "cars") if os.environ.get("VERCEL") else os.path.join(REPOSITORY_ROOT, "static", "uploads", "cars")
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except Exception:
    pass



def save_uploaded_image(file: UploadFile, folder: str) -> str:
    base_name, ext = os.path.splitext(file.filename or "image.jpg")
    clean_base = re.sub(r'[^\w\.-]', '_', base_name).strip('_')
    if not clean_base:
        clean_base = "upload"
    filename = f"{clean_base}{ext.lower()}"
    file_path = os.path.join(folder, filename)
    if os.path.exists(file_path):
        filename = f"{clean_base}_{uuid.uuid4().hex[:6]}{ext.lower()}"
    return filename


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


def invalidate_cars_cache():
    """Compatibility no-op: car reads always come directly from the database."""
    return None


@router.get("", response_model=list[CarResponse])
@router.get("/", response_model=list[CarResponse], include_in_schema=False)
async def get_cars(category: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(CarCatalog)
    if category:
        query = query.where(CarCatalog.category.ilike(f"%{category}%"))
    result = await db.execute(query.order_by(CarCatalog.list_price.asc()))
    return result.scalars().all()


@router.get("/{car_id_or_code}", response_model=CarResponse)
async def get_car_by_id_or_code(car_id_or_code: str, db: AsyncSession = Depends(get_db)):
    try:
        car_uuid = uuid.UUID(car_id_or_code)
        query = select(CarCatalog).where(CarCatalog.car_id == car_uuid)
    except ValueError:
        query = select(CarCatalog).where(
            (CarCatalog.vehicle_line.ilike(car_id_or_code)) |
            (CarCatalog.model_name.ilike(f"%{car_id_or_code}%"))
        )

    result = await db.execute(query)
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu xe này!")
    return car


def parse_bool(val: Any, default: bool = True) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    s = str(val).strip().lower()
    if s in ("true", "1", "t", "yes", "on", "active", "đang mở bán", "đang kinh doanh"):
        return True
    if s in ("false", "0", "f", "no", "off", "inactive", "tạm ngưng", "không kinh doanh"):
        return False
    return default


def _is_ebus(model_name: str | None, vehicle_line: str | None) -> bool:
    return bool(re.search(r"ebus", f"{model_name or ''} {vehicle_line or ''}", re.IGNORECASE))


def _extract_top_level_colors(raw_specs: dict[str, Any]) -> list[Any] | None:
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


@router.post("", response_model=CarResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=CarResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_car(
    # Primary fields
    model_name: str | None = Form(None),
    vehicle_line: str | None = Form(None),
    version: str | None = Form(None),
    category: str | None = Form("Personal"),
    list_price: int | None = Form(None),
    # Specs fields
    seat_count: int | None = Form(None),
    length_mm: int | None = Form(None),
    width_mm: int | None = Form(None),
    height_mm: int | None = Form(None),
    wheelbase_mm: int | None = Form(None),
    range_km: float | None = Form(None),
    maximum_power_kw: float | None = Form(None),
    maximum_torque_nm: float | None = Form(None),
    usable_battery_capacity: float | None = Form(None),
    additional_specs_json: str | None = Form("{}"),
    image_url: str | None = Form(None),
    is_active: Any | None = Form(None),
    image: UploadFile | None = File(None),
    # Fallback legacy fields
    name: str | None = Form(None),
    code: str | None = Form(None),
    base_price: int | None = Form(None),
    specs_json: str | None = Form("{}"),
    is_available: Any | None = Form(None),
    current_user: Account = Depends(require_roles(["admin", "consultant"])),
    db: AsyncSession = Depends(get_db),
):
    final_model_name = model_name or name
    if not final_model_name:
        raise HTTPException(status_code=400, detail="Vui lòng nhập tên mẫu xe!")

    final_price = list_price if list_price is not None else (base_price or 0)
    final_line = vehicle_line or code or final_model_name.replace("VinFast", "").strip()
    final_active = parse_bool(is_active) if is_active is not None else parse_bool(is_available, True)
    final_specs_str = additional_specs_json if additional_specs_json and additional_specs_json != "{}" else specs_json

    try:
        raw_specs = json.loads(final_specs_str) if final_specs_str else {}
    except Exception:
        raw_specs = {}

    car_id = uuid.uuid4()
    formatted_legacy_specs = format_car_legacy_additional_specs(
        car_id=car_id,
        model_name=final_model_name,
        version=version,
        range_km=range_km,
        list_price=final_price,
        seat_count=seat_count,
        power_kw=maximum_power_kw,
        torque_nm=maximum_torque_nm,
        battery_kwh=usable_battery_capacity,
        length_mm=length_mm,
        width_mm=width_mm,
        height_mm=height_mm,
        wheelbase_mm=wheelbase_mm,
        is_active=final_active,
        raw_specs=raw_specs
    )

    final_image_url = image_url
    if image and image.filename:
        filename = save_uploaded_image(image, UPLOAD_DIR)
        file_path = os.path.join(UPLOAD_DIR, filename)

        contents = await image.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        final_image_url = f"/static/uploads/cars/{filename}"

    new_car = CarCatalog(
        car_id=car_id,
        model_name=final_model_name,
        vehicle_line=final_line,
        version=version,
        category=category or "Personal",
        list_price=final_price,
        seat_count=seat_count,
        length_mm=length_mm,
        width_mm=width_mm,
        height_mm=height_mm,
        wheelbase_mm=wheelbase_mm,
        range_km=range_km,
        maximum_power_kw=maximum_power_kw,
        maximum_torque_nm=maximum_torque_nm,
        usable_battery_capacity=usable_battery_capacity,
        additional_specs=formatted_legacy_specs,
        image_url=final_image_url,
        colors=None if _is_ebus(final_model_name, final_line) else (_extract_top_level_colors(raw_specs) or []),
        is_active=final_active,
    )
    db.add(new_car)
    await db.commit()
    await db.refresh(new_car)
    invalidate_cars_cache()
    return new_car


@router.put("/{car_id}", response_model=CarResponse)
async def update_car(
    car_id: uuid.UUID,
    model_name: str | None = Form(None),
    vehicle_line: str | None = Form(None),
    version: str | None = Form(None),
    category: str | None = Form(None),
    list_price: int | None = Form(None),
    seat_count: int | None = Form(None),
    length_mm: int | None = Form(None),
    width_mm: int | None = Form(None),
    height_mm: int | None = Form(None),
    wheelbase_mm: int | None = Form(None),
    range_km: float | None = Form(None),
    maximum_power_kw: float | None = Form(None),
    maximum_torque_nm: float | None = Form(None),
    usable_battery_capacity: float | None = Form(None),
    additional_specs_json: str | None = Form(None),
    image_url: str | None = Form(None),
    is_active: Any | None = Form(None),
    image: UploadFile | None = File(None),
    # Fallback legacy fields
    name: str | None = Form(None),
    code: str | None = Form(None),
    base_price: int | None = Form(None),
    specs_json: str | None = Form(None),
    is_available: Any | None = Form(None),
    current_user: Account = Depends(require_roles(["admin", "consultant"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CarCatalog).where(CarCatalog.car_id == car_id))
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu xe!")

    if model_name is not None:
        car.model_name = model_name
    elif name is not None:
        car.model_name = name

    if vehicle_line is not None:
        car.vehicle_line = vehicle_line
    elif code is not None:
        car.vehicle_line = code

    if version is not None:
        car.version = version

    if category is not None:
        car.category = category

    if list_price is not None:
        car.list_price = list_price
    elif base_price is not None:
        car.list_price = base_price

    if seat_count is not None:
        car.seat_count = seat_count
    if length_mm is not None:
        car.length_mm = length_mm
    if width_mm is not None:
        car.width_mm = width_mm
    if height_mm is not None:
        car.height_mm = height_mm
    if wheelbase_mm is not None:
        car.wheelbase_mm = wheelbase_mm
    if range_km is not None:
        car.range_km = range_km
    if maximum_power_kw is not None:
        car.maximum_power_kw = maximum_power_kw
    if maximum_torque_nm is not None:
        car.maximum_torque_nm = maximum_torque_nm
    if usable_battery_capacity is not None:
        car.usable_battery_capacity = usable_battery_capacity

    if is_active is not None:
        car.is_active = parse_bool(is_active)
    elif is_available is not None:
        car.is_active = parse_bool(is_available)

    final_specs_str = additional_specs_json or specs_json
    raw_specs = car.additional_specs or {}
    if final_specs_str:
        try:
            raw_specs = json.loads(final_specs_str)
        except Exception:
            pass

    car.additional_specs = format_car_legacy_additional_specs(
        car_id=car.car_id,
        model_name=car.model_name,
        version=car.version,
        range_km=car.range_km,
        list_price=car.list_price,
        seat_count=car.seat_count,
        power_kw=car.maximum_power_kw,
        torque_nm=car.maximum_torque_nm,
        battery_kwh=car.usable_battery_capacity,
        length_mm=car.length_mm,
        width_mm=car.width_mm,
        height_mm=car.height_mm,
        wheelbase_mm=car.wheelbase_mm,
        is_active=car.is_active,
        raw_specs=raw_specs
    )

    if _is_ebus(car.model_name, car.vehicle_line):
        car.colors = None
    elif isinstance(raw_specs, dict) and "colors" in raw_specs:
        car.colors = _extract_top_level_colors(raw_specs) or []

    if image and image.filename:
        filename = save_uploaded_image(image, UPLOAD_DIR)
        file_path = os.path.join(UPLOAD_DIR, filename)

        contents = await image.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        car.image_url = f"/static/uploads/cars/{filename}"
    elif image_url is not None:
        car.image_url = image_url

    await db.commit()
    await db.refresh(car)
    invalidate_cars_cache()
    return car


@router.delete("/{car_id}", status_code=status.HTTP_200_OK)
async def delete_car(
    car_id: uuid.UUID,
    current_user: Account = Depends(require_roles(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CarCatalog).where(CarCatalog.car_id == car_id))
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu xe!")

    await db.delete(car)
    await db.commit()
    invalidate_cars_cache()
    return {"message": f"Đã xóa thành công mẫu xe {car.model_name}"}
