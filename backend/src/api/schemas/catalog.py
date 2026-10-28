import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

OptionalNonNegativeInt = Annotated[int | None, Field(ge=0)]
OptionalNonNegativeFloat = Annotated[float | None, Field(ge=0)]


class CarCreate(BaseModel):
    model_name: str = Field(..., min_length=2, max_length=100, examples=["VinFast VF 6 Plus"])
    vehicle_line: str | None = Field(None, max_length=50, description="Mặc định suy ra từ model_name")
    version: str | None = Field(None, max_length=50)
    category: str = Field("Personal", min_length=2, max_length=50)
    list_price: int = Field(0, ge=0)
    seat_count: int | None = Field(None, ge=1, le=80)
    length_mm: OptionalNonNegativeInt = None
    width_mm: OptionalNonNegativeInt = None
    height_mm: OptionalNonNegativeInt = None
    wheelbase_mm: OptionalNonNegativeInt = None
    range_km: OptionalNonNegativeFloat = None
    maximum_power_kw: OptionalNonNegativeFloat = None
    maximum_torque_nm: OptionalNonNegativeFloat = None
    usable_battery_capacity: OptionalNonNegativeFloat = None
    additional_specs: dict[str, Any] = Field(default_factory=dict)
    colors: list[Any] | None = None
    image_url: str | None = Field(None, max_length=2_000)
    is_active: bool = True


class CarUpdate(BaseModel):
    """Partial update: only fields present in the JSON body are changed."""

    model_name: str | None = Field(None, min_length=2, max_length=100)
    vehicle_line: str | None = Field(None, min_length=1, max_length=50)
    version: str | None = Field(None, max_length=50)
    category: str | None = Field(None, min_length=2, max_length=50)
    list_price: int | None = Field(None, ge=0)
    seat_count: int | None = Field(None, ge=1, le=80)
    length_mm: OptionalNonNegativeInt = None
    width_mm: OptionalNonNegativeInt = None
    height_mm: OptionalNonNegativeInt = None
    wheelbase_mm: OptionalNonNegativeInt = None
    range_km: OptionalNonNegativeFloat = None
    maximum_power_kw: OptionalNonNegativeFloat = None
    maximum_torque_nm: OptionalNonNegativeFloat = None
    usable_battery_capacity: OptionalNonNegativeFloat = None
    additional_specs: dict[str, Any] | None = None
    colors: list[Any] | None = None
    image_url: str | None = Field(None, max_length=2_000)
    is_active: bool | None = None


class CarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    car_id: uuid.UUID
    id: uuid.UUID
    model_name: str
    vehicle_line: str
    name: str
    code: str
    version: str | None = None
    category: str = "Personal"
    list_price: int = 0
    base_price: int = 0
    image_url: str | None = None
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
    additional_specs: dict[str, Any] | None = None
    specs: dict[str, Any] | None = None
    is_active: bool = True
    is_available: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MotorbikeCreate(BaseModel):
    model_name: str = Field(..., min_length=2, max_length=100, examples=["VinFast Evo Grand"])
    vehicle_line: str | None = Field(None, max_length=50)
    version: str | None = Field(None, max_length=50)
    category: str = Field("motorbike", min_length=2, max_length=50)
    list_price: int = Field(0, ge=0)
    description: str | None = Field(None, max_length=5_000)
    range_km: OptionalNonNegativeFloat = None
    charging_time_minutes: OptionalNonNegativeInt = None
    battery_type: str | None = Field(None, max_length=100)
    battery_quantity: int | None = Field(None, ge=0, le=10)
    battery_capacity_kwh: OptionalNonNegativeFloat = None
    motor_type: str | None = Field(None, max_length=100)
    maximum_power_w: OptionalNonNegativeFloat = None
    maximum_speed_kmh: OptionalNonNegativeFloat = None
    weight_kg: OptionalNonNegativeFloat = None
    length_mm: OptionalNonNegativeInt = None
    width_mm: OptionalNonNegativeInt = None
    height_mm: OptionalNonNegativeInt = None
    front_brake: str | None = Field(None, max_length=100)
    rear_brake: str | None = Field(None, max_length=100)
    front_suspension: str | None = Field(None, max_length=100)
    rear_suspension: str | None = Field(None, max_length=100)
    additional_specs: dict[str, Any] = Field(default_factory=dict)
    colors: list[Any] | None = None
    image_url: str | None = Field(None, max_length=2_000)
    is_active: bool = True


class MotorbikeUpdate(BaseModel):
    model_name: str | None = Field(None, min_length=2, max_length=100)
    vehicle_line: str | None = Field(None, min_length=1, max_length=50)
    version: str | None = Field(None, max_length=50)
    category: str | None = Field(None, min_length=2, max_length=50)
    list_price: int | None = Field(None, ge=0)
    description: str | None = Field(None, max_length=5_000)
    range_km: OptionalNonNegativeFloat = None
    charging_time_minutes: OptionalNonNegativeInt = None
    battery_type: str | None = Field(None, max_length=100)
    battery_quantity: int | None = Field(None, ge=0, le=10)
    battery_capacity_kwh: OptionalNonNegativeFloat = None
    motor_type: str | None = Field(None, max_length=100)
    maximum_power_w: OptionalNonNegativeFloat = None
    maximum_speed_kmh: OptionalNonNegativeFloat = None
    weight_kg: OptionalNonNegativeFloat = None
    length_mm: OptionalNonNegativeInt = None
    width_mm: OptionalNonNegativeInt = None
    height_mm: OptionalNonNegativeInt = None
    front_brake: str | None = Field(None, max_length=100)
    rear_brake: str | None = Field(None, max_length=100)
    front_suspension: str | None = Field(None, max_length=100)
    rear_suspension: str | None = Field(None, max_length=100)
    additional_specs: dict[str, Any] | None = None
    colors: list[Any] | None = None
    image_url: str | None = Field(None, max_length=2_000)
    is_active: bool | None = None


class MotorbikeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    motorbike_id: uuid.UUID
    id: uuid.UUID
    model_name: str
    vehicle_line: str
    name: str
    code: str
    version: str | None = None
    category: str = "motorbike"
    list_price: int = 0
    base_price: int = 0
    colors: list[Any] | None = None
    image_url: str | None = None
    range_km: float | None = None
    charging_time_minutes: int | None = None
    battery_type: str | None = None
    battery_quantity: int | None = None
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
    additional_specs: dict[str, Any] | None = None
    specs: dict[str, Any] | None = None
    is_active: bool = True
    is_available: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
