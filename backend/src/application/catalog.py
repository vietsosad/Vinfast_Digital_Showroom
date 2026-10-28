"""Use cases for the car and motorbike catalog."""

from __future__ import annotations

from dataclasses import fields
from typing import Any
from uuid import UUID, uuid4

from src.application.uploads import DEFAULT_MAX_IMAGE_BYTES, storage_filename, validate_image
from src.domain.catalog import Car, Motorbike, VehicleSummary, summarize
from src.domain.catalog_specs import (
    extract_top_level_colors,
    format_car_legacy_additional_specs,
    format_motorbike_legacy_additional_specs,
    is_ebus,
)
from src.domain.errors import NotFoundError, ValidationError
from src.domain.files import FileStorage, UploadedFile
from src.domain.unit_of_work import UnitOfWork

CAR_FIELDS = {f.name for f in fields(Car)} - {"car_id", "created_at", "updated_at"}
MOTORBIKE_FIELDS = {f.name for f in fields(Motorbike)} - {"motorbike_id", "created_at", "updated_at"}
MOTORBIKE_SPEC_COLUMNS = ("front_brake", "rear_brake", "front_suspension", "rear_suspension")


def parse_vehicle_id(value: str) -> UUID | None:
    try:
        return UUID(str(value))
    except ValueError:
        return None


def derive_vehicle_line(model_name: str, vehicle_line: str | None) -> str:
    line = (vehicle_line or "").strip() or model_name.replace("VinFast", "").strip()
    if not line:
        raise ValidationError("Không xác định được dòng xe")
    return line


async def find_vehicle(uow: UnitOfWork, vehicle_id: UUID) -> VehicleSummary:
    """Load the authoritative name and price of any catalog vehicle."""
    vehicle = await uow.cars.get(vehicle_id) or await uow.motorbikes.get(vehicle_id)
    if vehicle is None:
        raise NotFoundError("Không tìm thấy mẫu xe trong danh mục")
    summary = summarize(vehicle)
    if not summary.is_active:
        raise ValidationError("Mẫu xe này hiện tạm ngưng kinh doanh")
    return summary


class CarCatalogService:
    def __init__(self, uow: UnitOfWork, storage: FileStorage, max_image_bytes: int = DEFAULT_MAX_IMAGE_BYTES):
        self.uow = uow
        self.storage = storage
        self.max_image_bytes = max_image_bytes

    async def list(self, category: str | None = None) -> list[Car]:
        return await self.uow.cars.list((category or "").strip() or None)

    async def get(self, id_or_code: str) -> Car:
        car_id = parse_vehicle_id(id_or_code)
        car = await self.uow.cars.get(car_id) if car_id else await self.uow.cars.find_by_code_or_name(id_or_code)
        if car is None:
            raise NotFoundError("Không tìm thấy mẫu xe này")
        return car

    async def create(self, data: dict[str, Any]) -> Car:
        values = {key: value for key, value in data.items() if key in CAR_FIELDS}
        model_name = (values.pop("model_name", "") or "").strip()
        if len(model_name) < 2:
            raise ValidationError("Vui lòng nhập tên mẫu xe")
        raw_specs = values.pop("additional_specs", None) or {}
        explicit_colors = values.pop("colors", None)
        car = Car(
            car_id=uuid4(),
            model_name=model_name,
            vehicle_line=derive_vehicle_line(model_name, values.pop("vehicle_line", None)),
            list_price=values.pop("list_price", 0) or 0,
            **values,
        )
        car.category = car.category or "Personal"
        self._refresh_derived_fields(car, raw_specs, explicit_colors, colors_given=explicit_colors is not None)
        car = await self.uow.cars.add(car)
        await self.uow.commit()
        return car

    async def update(self, car_id: UUID, changes: dict[str, Any]) -> Car:
        car = await self._require(car_id)
        values = {key: value for key, value in changes.items() if key in CAR_FIELDS}
        raw_specs = values.pop("additional_specs", None)
        colors_given = "colors" in values
        explicit_colors = values.pop("colors", None)
        for key, value in values.items():
            if value is None and key in {"model_name", "vehicle_line", "list_price", "category", "is_active"}:
                continue
            setattr(car, key, value)
        self._refresh_derived_fields(
            car,
            raw_specs if raw_specs is not None else car.additional_specs or {},
            explicit_colors,
            colors_given=colors_given,
            specs_given=raw_specs is not None,
        )
        car = await self.uow.cars.save(car)
        await self.uow.commit()
        return car

    async def delete(self, car_id: UUID) -> Car:
        car = await self._require(car_id)
        await self.uow.cars.delete(car_id)
        await self.uow.commit()
        return car

    async def replace_image(self, car_id: UUID, upload: UploadedFile) -> Car:
        car = await self._require(car_id)
        extension = validate_image(upload, self.max_image_bytes)
        url = self.storage.save("uploads/cars", storage_filename(upload.filename, extension), upload.content)
        try:
            car.image_url = url
            car = await self.uow.cars.save(car)
            await self.uow.commit()
        except BaseException:
            self.storage.delete(url)
            raise
        return car

    async def _require(self, car_id: UUID) -> Car:
        car = await self.uow.cars.get(car_id)
        if car is None:
            raise NotFoundError("Không tìm thấy mẫu xe")
        return car

    @staticmethod
    def _refresh_derived_fields(
        car: Car,
        raw_specs: dict[str, Any],
        explicit_colors: list[Any] | None,
        *,
        colors_given: bool,
        specs_given: bool = True,
    ) -> None:
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
            raw_specs=raw_specs,
        )
        if is_ebus(car.model_name, car.vehicle_line):
            car.colors = None
        elif colors_given:
            car.colors = explicit_colors or []
        elif specs_given and isinstance(raw_specs, dict) and "colors" in raw_specs:
            car.colors = extract_top_level_colors(raw_specs) or []
        elif car.colors is None:
            car.colors = extract_top_level_colors(raw_specs) or []


class MotorbikeCatalogService:
    def __init__(self, uow: UnitOfWork, storage: FileStorage, max_image_bytes: int = DEFAULT_MAX_IMAGE_BYTES):
        self.uow = uow
        self.storage = storage
        self.max_image_bytes = max_image_bytes

    async def list(self, category: str | None = None) -> list[Motorbike]:
        return await self.uow.motorbikes.list((category or "").strip() or None)

    async def get(self, id_or_code: str) -> Motorbike:
        motorbike_id = parse_vehicle_id(id_or_code)
        if motorbike_id:
            motorbike = await self.uow.motorbikes.get(motorbike_id)
        else:
            motorbike = await self.uow.motorbikes.find_by_code_or_name(id_or_code)
        if motorbike is None:
            raise NotFoundError("Không tìm thấy mẫu xe máy điện này")
        return motorbike

    async def create(self, data: dict[str, Any]) -> Motorbike:
        description = data.get("description")
        values = {key: value for key, value in data.items() if key in MOTORBIKE_FIELDS}
        model_name = (values.pop("model_name", "") or "").strip()
        if len(model_name) < 2:
            raise ValidationError("Vui lòng nhập tên mẫu xe máy điện")
        raw_specs = values.pop("additional_specs", None) or {}
        colors = values.pop("colors", None)
        motorbike = Motorbike(
            motorbike_id=uuid4(),
            model_name=model_name,
            vehicle_line=derive_vehicle_line(model_name, values.pop("vehicle_line", None)),
            list_price=values.pop("list_price", 0) or 0,
            **values,
        )
        motorbike.category = motorbike.category or "motorbike"
        motorbike.battery_quantity = motorbike.battery_quantity or 1
        motorbike.colors = colors if colors is not None else raw_specs.get("colors", []) or []
        for column in MOTORBIKE_SPEC_COLUMNS:
            if getattr(motorbike, column) is None:
                setattr(motorbike, column, raw_specs.get(column))
        self._refresh_specs(motorbike, raw_specs, description)
        motorbike = await self.uow.motorbikes.add(motorbike)
        await self.uow.commit()
        return motorbike

    async def update(self, motorbike_id: UUID, changes: dict[str, Any]) -> Motorbike:
        motorbike = await self._require(motorbike_id)
        description = changes.get("description")
        values = {key: value for key, value in changes.items() if key in MOTORBIKE_FIELDS}
        raw_specs = values.pop("additional_specs", None)
        for key, value in values.items():
            if value is None and key in {"model_name", "vehicle_line", "list_price", "category", "is_active", "colors"}:
                continue
            setattr(motorbike, key, value)
        specs = raw_specs if raw_specs is not None else motorbike.additional_specs or {}
        if raw_specs is not None:
            if "colors" in raw_specs and "colors" not in values:
                motorbike.colors = raw_specs.get("colors") or []
            for column in MOTORBIKE_SPEC_COLUMNS:
                if column in raw_specs and column not in values:
                    setattr(motorbike, column, raw_specs.get(column))
        self._refresh_specs(motorbike, specs, description)
        motorbike = await self.uow.motorbikes.save(motorbike)
        await self.uow.commit()
        return motorbike

    async def delete(self, motorbike_id: UUID) -> Motorbike:
        motorbike = await self._require(motorbike_id)
        await self.uow.motorbikes.delete(motorbike_id)
        await self.uow.commit()
        return motorbike

    async def replace_image(self, motorbike_id: UUID, upload: UploadedFile) -> Motorbike:
        motorbike = await self._require(motorbike_id)
        extension = validate_image(upload, self.max_image_bytes)
        url = self.storage.save("uploads/motorbikes", storage_filename(upload.filename, extension), upload.content)
        try:
            motorbike.image_url = url
            motorbike = await self.uow.motorbikes.save(motorbike)
            await self.uow.commit()
        except BaseException:
            self.storage.delete(url)
            raise
        return motorbike

    async def _require(self, motorbike_id: UUID) -> Motorbike:
        motorbike = await self.uow.motorbikes.get(motorbike_id)
        if motorbike is None:
            raise NotFoundError("Không tìm thấy mẫu xe máy điện")
        return motorbike

    @staticmethod
    def _refresh_specs(motorbike: Motorbike, raw_specs: dict[str, Any], description: str | None) -> None:
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
            description=description,
        )
