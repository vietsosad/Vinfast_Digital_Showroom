from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, TypeVar
from uuid import UUID


class VehicleKind(str, Enum):
    CAR = "car"
    MOTORBIKE = "motorbike"


class _CompatibilityAliases:
    """Read-only aliases kept for API clients written against the old schema."""

    model_name: str
    vehicle_line: str
    list_price: int
    additional_specs: dict[str, Any]
    is_active: bool

    @property
    def name(self) -> str:
        return self.model_name

    @property
    def code(self) -> str:
        return self.vehicle_line

    @property
    def base_price(self) -> int:
        return self.list_price or 0

    @property
    def specs(self) -> dict[str, Any]:
        return self.additional_specs

    @property
    def is_available(self) -> bool:
        return self.is_active


@dataclass
class Car(_CompatibilityAliases):
    car_id: UUID
    model_name: str
    vehicle_line: str
    list_price: int
    version: str | None = None
    category: str = "Personal"
    image_url: str | None = None
    # None is intentional for EBus: no verified exterior-color catalog exists.
    colors: list[Any] | None = None
    seat_count: int | None = None
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    wheelbase_mm: int | None = None
    range_km: float | None = None
    maximum_power_kw: float | None = None
    maximum_torque_nm: float | None = None
    usable_battery_capacity: float | None = None
    additional_specs: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def id(self) -> UUID:
        return self.car_id


@dataclass
class Motorbike(_CompatibilityAliases):
    motorbike_id: UUID
    model_name: str
    vehicle_line: str
    list_price: int
    version: str | None = None
    category: str = "motorbike"
    image_url: str | None = None
    colors: list[Any] = field(default_factory=list)
    range_km: float | None = None
    charging_time_minutes: int | None = None
    battery_type: str | None = None
    battery_quantity: int | None = 1
    battery_capacity_kwh: float | None = None
    motor_type: str | None = None
    maximum_power_w: float | None = None
    maximum_speed_kmh: float | None = None
    weight_kg: float | None = None
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    front_brake: str | None = None
    rear_brake: str | None = None
    front_suspension: str | None = None
    rear_suspension: str | None = None
    additional_specs: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def id(self) -> UUID:
        return self.motorbike_id


@dataclass(frozen=True)
class VehicleSummary:
    """The catalog facts a quote or booking is allowed to rely on."""

    vehicle_id: UUID
    kind: VehicleKind
    name: str
    list_price: int
    is_active: bool


def summarize(vehicle: Car | Motorbike) -> VehicleSummary:
    kind = VehicleKind.CAR if isinstance(vehicle, Car) else VehicleKind.MOTORBIKE
    return VehicleSummary(
        vehicle_id=vehicle.id,
        kind=kind,
        name=vehicle.model_name,
        list_price=vehicle.list_price or 0,
        is_active=vehicle.is_active,
    )


VehicleT = TypeVar("VehicleT", Car, Motorbike)


class VehicleRepository(Protocol[VehicleT]):
    async def list(self, category: str | None = None) -> list[VehicleT]: ...

    async def get(self, vehicle_id: UUID) -> VehicleT | None: ...

    async def find_by_code_or_name(self, term: str) -> VehicleT | None: ...

    async def add(self, vehicle: VehicleT) -> VehicleT: ...

    async def save(self, vehicle: VehicleT) -> VehicleT: ...

    async def delete(self, vehicle_id: UUID) -> bool: ...


CarRepository = VehicleRepository[Car]
MotorbikeRepository = VehicleRepository[Motorbike]
