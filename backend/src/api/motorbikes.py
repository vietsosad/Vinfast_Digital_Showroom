import json
import os
import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.domain import Account, MotorbikeCatalog
from src.models.schemas import EScooterResponse
from src.services.database import get_db
from src.services.security import require_roles

router = APIRouter()

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
UPLOAD_DIR = os.path.join("/tmp", "uploads", "motorbikes") if os.environ.get("VERCEL") else os.path.join(REPOSITORY_ROOT, "static", "uploads", "motorbikes")
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


_motorbikes_cache: list[Any] | None = None

def invalidate_motorbikes_cache():
    global _motorbikes_cache
    _motorbikes_cache = None


@router.get("", response_model=list[EScooterResponse])
@router.get("/", response_model=list[EScooterResponse], include_in_schema=False)
async def get_motorbikes(category: str | None = None, db: AsyncSession = Depends(get_db)):
    global _motorbikes_cache
    if not category and _motorbikes_cache is not None:
        return _motorbikes_cache

    query = select(MotorbikeCatalog)
    if category:
        query = query.where(MotorbikeCatalog.category.ilike(f"%{category}%"))
    result = await db.execute(query.order_by(MotorbikeCatalog.list_price.asc()))
    motorbikes = result.scalars().all()
    if not category:
        _motorbikes_cache = motorbikes
    return motorbikes


@router.get("/{motorbike_id_or_code}", response_model=EScooterResponse)
async def get_motorbike_by_id_or_code(motorbike_id_or_code: str, db: AsyncSession = Depends(get_db)):
    try:
        scooter_uuid = uuid.UUID(motorbike_id_or_code)
        query = select(MotorbikeCatalog).where(MotorbikeCatalog.motorbike_id == scooter_uuid)
    except ValueError:
        query = select(MotorbikeCatalog).where(
            (MotorbikeCatalog.vehicle_line.ilike(motorbike_id_or_code)) |
            (MotorbikeCatalog.model_name.ilike(f"%{motorbike_id_or_code}%"))
        )

    result = await db.execute(query)
    motorbike = result.scalar_one_or_none()
    if not motorbike:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu xe máy điện này!")
    return motorbike


@router.post("", response_model=EScooterResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=EScooterResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_motorbike(
    # Primary fields
    model_name: str | None = Form(None),
    vehicle_line: str | None = Form(None),
    version: str | None = Form(None),
    category: str | None = Form("motorbike"),
    list_price: int | None = Form(None),
    description: str | None = Form(None),
    # Specs fields
    range_km: float | None = Form(None),
    charging_time_minutes: int | None = Form(None),
    battery_type: str | None = Form(None),
    battery_quantity: int | None = Form(None),
    battery_capacity_kwh: float | None = Form(None),
    motor_type: str | None = Form(None),
    maximum_motor_power_w: float | None = Form(None),
    maximum_power_w: float | None = Form(None),
    maximum_speed_kmh: float | None = Form(None),
    weight_kg: float | None = Form(None),
    length_mm: int | None = Form(None),
    width_mm: int | None = Form(None),
    height_mm: int | None = Form(None),
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
    final_name = model_name or name
    if not final_name:
        raise HTTPException(status_code=400, detail="Vui lòng nhập tên mẫu xe máy điện!")

    final_price = list_price if list_price is not None else (base_price or 0)
    final_line = vehicle_line or code or final_name.replace("VinFast", "").strip()
    final_active = parse_bool(is_active) if is_active is not None else parse_bool(is_available, True)
    final_specs_str = additional_specs_json if (additional_specs_json and additional_specs_json != "{}") else specs_json

    try:
        raw_specs = json.loads(final_specs_str) if final_specs_str else {}
    except Exception:
        raw_specs = {}

    motorbike_id = uuid.uuid4()
    max_power = maximum_motor_power_w if maximum_motor_power_w is not None else maximum_power_w

    formatted_legacy_specs = format_motorbike_legacy_additional_specs(
        motorbike_id=motorbike_id,
        model_name=final_name,
        version=version,
        range_km=range_km,
        list_price=final_price,
        length_mm=length_mm,
        width_mm=width_mm,
        height_mm=height_mm,
        is_active=final_active,
        raw_specs=raw_specs,
        motor_type=motor_type,
        battery_type=battery_type,
        battery_quantity=battery_quantity,
        battery_capacity_kwh=battery_capacity_kwh,
        maximum_motor_power_w=max_power,
        maximum_speed_kmh=maximum_speed_kmh,
        charging_time_minutes=charging_time_minutes,
        description=description
    )

    final_image_url = image_url
    if image and image.filename:
        filename = save_uploaded_image(image, UPLOAD_DIR)
        file_path = os.path.join(UPLOAD_DIR, filename)

        contents = await image.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        final_image_url = f"/static/uploads/motorbikes/{filename}"

    db_colors = raw_specs.get("colors", [])
    db_front_brake = raw_specs.get("front_brake")
    db_rear_brake = raw_specs.get("rear_brake")
    db_front_suspension = raw_specs.get("front_suspension")
    db_rear_suspension = raw_specs.get("rear_suspension")

    new_motorbike = MotorbikeCatalog(
        motorbike_id=motorbike_id,
        model_name=final_name,
        vehicle_line=final_line,
        version=version,
        category=category or "motorbike",
        list_price=final_price,
        range_km=range_km,
        charging_time_minutes=charging_time_minutes,
        battery_type=battery_type,
        battery_quantity=battery_quantity or 1,
        battery_capacity_kwh=battery_capacity_kwh,
        motor_type=motor_type,
        maximum_power_w=max_power,
        maximum_speed_kmh=maximum_speed_kmh,
        weight_kg=weight_kg,
        length_mm=length_mm,
        width_mm=width_mm,
        height_mm=height_mm,
        colors=db_colors,
        front_brake=db_front_brake,
        rear_brake=db_rear_brake,
        front_suspension=db_front_suspension,
        rear_suspension=db_rear_suspension,
        additional_specs=formatted_legacy_specs,
        image_url=final_image_url,
        is_active=final_active,
    )
    db.add(new_motorbike)
    await db.commit()
    await db.refresh(new_motorbike)
    invalidate_motorbikes_cache()
    return new_motorbike


@router.put("/{motorbike_id}", response_model=EScooterResponse)
async def update_motorbike(
    motorbike_id: uuid.UUID,
    # Primary fields
    model_name: str | None = Form(None),
    vehicle_line: str | None = Form(None),
    version: str | None = Form(None),
    category: str | None = Form(None),
    list_price: int | None = Form(None),
    description: str | None = Form(None),
    # Specs fields
    range_km: float | None = Form(None),
    charging_time_minutes: int | None = Form(None),
    battery_type: str | None = Form(None),
    battery_quantity: int | None = Form(None),
    battery_capacity_kwh: float | None = Form(None),
    motor_type: str | None = Form(None),
    maximum_motor_power_w: float | None = Form(None),
    maximum_power_w: float | None = Form(None),
    maximum_speed_kmh: float | None = Form(None),
    weight_kg: float | None = Form(None),
    length_mm: int | None = Form(None),
    width_mm: int | None = Form(None),
    height_mm: int | None = Form(None),
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
    result = await db.execute(select(MotorbikeCatalog).where(MotorbikeCatalog.motorbike_id == motorbike_id))
    motorbike = result.scalar_one_or_none()
    if not motorbike:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu xe máy điện!")

    if model_name is not None:
        motorbike.model_name = model_name
    elif name is not None:
        motorbike.model_name = name

    if vehicle_line is not None:
        motorbike.vehicle_line = vehicle_line
    elif code is not None:
        motorbike.vehicle_line = code

    if version is not None:
        motorbike.version = version

    if category is not None:
        motorbike.category = category

    if list_price is not None:
        motorbike.list_price = list_price
    elif base_price is not None:
        motorbike.list_price = base_price

    if is_active is not None:
        motorbike.is_active = parse_bool(is_active)
    elif is_available is not None:
        motorbike.is_active = parse_bool(is_available)

    if range_km is not None: motorbike.range_km = range_km
    if charging_time_minutes is not None: motorbike.charging_time_minutes = charging_time_minutes
    if battery_type is not None: motorbike.battery_type = battery_type
    if battery_quantity is not None: motorbike.battery_quantity = battery_quantity
    if battery_capacity_kwh is not None: motorbike.battery_capacity_kwh = battery_capacity_kwh
    if motor_type is not None: motorbike.motor_type = motor_type

    max_power = maximum_motor_power_w if maximum_motor_power_w is not None else maximum_power_w
    if max_power is not None: motorbike.maximum_power_w = max_power

    if maximum_speed_kmh is not None: motorbike.maximum_speed_kmh = maximum_speed_kmh
    if weight_kg is not None: motorbike.weight_kg = weight_kg
    if length_mm is not None: motorbike.length_mm = length_mm
    if width_mm is not None: motorbike.width_mm = width_mm
    if height_mm is not None: motorbike.height_mm = height_mm

    final_specs_str = additional_specs_json or specs_json
    raw_specs = motorbike.additional_specs or {}
    if final_specs_str:
        try:
            raw_specs = json.loads(final_specs_str)
        except Exception:
            pass

    if "colors" in raw_specs: motorbike.colors = raw_specs.get("colors", [])
    if "front_brake" in raw_specs: motorbike.front_brake = raw_specs.get("front_brake")
    if "rear_brake" in raw_specs: motorbike.rear_brake = raw_specs.get("rear_brake")
    if "front_suspension" in raw_specs: motorbike.front_suspension = raw_specs.get("front_suspension")
    if "rear_suspension" in raw_specs: motorbike.rear_suspension = raw_specs.get("rear_suspension")

    motorbike.additional_specs = format_motorbike_legacy_additional_specs(
        motorbike_id=motorbike.motorbike_id,
        model_name=motorbike.model_name,
        version=motorbike.version,
        range_km=motorbike.range_km,
        list_price=motorbike.list_price,
        length_mm=motorbike.length_mm,
        width_mm=motorbike.width_mm,
        height_mm=motorbike.height_mm,
        is_active=motorbike.is_active,
        raw_specs=raw_specs,
        motor_type=motorbike.motor_type,
        battery_type=motorbike.battery_type,
        battery_quantity=motorbike.battery_quantity,
        battery_capacity_kwh=motorbike.battery_capacity_kwh,
        maximum_motor_power_w=motorbike.maximum_power_w,
        maximum_speed_kmh=motorbike.maximum_speed_kmh,
        charging_time_minutes=motorbike.charging_time_minutes,
        description=description
    )

    if image and image.filename:
        filename = save_uploaded_image(image, UPLOAD_DIR)
        file_path = os.path.join(UPLOAD_DIR, filename)

        contents = await image.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        motorbike.image_url = f"/static/uploads/motorbikes/{filename}"
    elif image_url is not None:
        motorbike.image_url = image_url

    await db.commit()
    await db.refresh(motorbike)
    invalidate_motorbikes_cache()
    return motorbike


@router.delete("/{motorbike_id}", status_code=status.HTTP_200_OK)
async def delete_motorbike(
    motorbike_id: uuid.UUID,
    current_user: Account = Depends(require_roles(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MotorbikeCatalog).where(MotorbikeCatalog.motorbike_id == motorbike_id))
    motorbike = result.scalar_one_or_none()
    if not motorbike:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu xe máy điện!")

    await db.delete(motorbike)
    await db.commit()
    invalidate_motorbikes_cache()
    return {"message": f"Đã xóa thành công mẫu xe máy điện {motorbike.model_name}"}
