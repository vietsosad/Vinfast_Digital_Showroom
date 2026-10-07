import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth Schemas ---
class UserRegister(BaseModel):
    email: EmailStr
    phone: str = Field(..., min_length=9, max_length=15)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    role: str = "customer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    phone: str
    full_name: str
    role: str
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- Car Schemas ---
class CarBase(BaseModel):
    model_name: str = Field(..., min_length=2, max_length=100)
    vehicle_line: str = Field(..., min_length=1, max_length=50)
    version: str | None = None
    category: str = Field(default="Personal", min_length=2, max_length=50)
    list_price: int = Field(default=0, ge=0)
    seat_count: int | None = None
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    wheelbase_mm: int | None = None
    range_km: float | None = None
    maximum_power_kw: float | None = None
    maximum_torque_nm: float | None = None
    usable_battery_capacity: float | None = None
    additional_specs: dict[str, Any] | None = Field(default_factory=dict)
    image_url: str | None = None
    colors: Any | None = None
    is_active: bool = True

    # Compatibility properties
    name: str | None = None
    code: str | None = None
    base_price: int | None = None
    specs: dict[str, Any] | None = None
    is_available: bool | None = None


class CarCreate(CarBase):
    pass


class CarUpdate(BaseModel):
    model_name: str | None = None
    vehicle_line: str | None = None
    version: str | None = None
    category: str | None = None
    list_price: int | None = None
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
    image_url: str | None = None
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
    list_price: int | None = 0
    base_price: int | None = 0
    battery_buy_price: int | None = None
    battery_rent_monthly: int | None = None
    description: str | None = None
    image_url: str | None = None
    colors: Any | None = None
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


# --- E-Scooter / Motorbike Schemas ---
class EScooterBase(BaseModel):
    model_name: str = Field(..., min_length=2, max_length=100)
    vehicle_line: str = Field(..., min_length=1, max_length=50)
    version: str | None = None
    category: str = Field(default="Scooter", min_length=2, max_length=50)
    list_price: int | None = Field(default=0, ge=0)
    range_km: float | None = None
    image_url: str | None = None
    is_active: bool = True


class EScooterCreate(EScooterBase):
    pass


class EScooterUpdate(BaseModel):
    model_name: str | None = None
    vehicle_line: str | None = None
    category: str | None = None
    list_price: int | None = None
    image_url: str | None = None
    is_active: bool | None = None


class EScooterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    motorbike_id: uuid.UUID | None = None
    id: uuid.UUID
    model_name: str
    vehicle_line: str
    name: str
    code: str
    version: str | None = None
    category: str = "Scooter"
    list_price: int | None = 0
    base_price: int | None = 0
    colors: Any | None = None
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


# --- Quote Schemas ---
class QuoteCreate(BaseModel):
    user_id: str | None = None
    customer_name: str
    customer_email: EmailStr | None = None
    customer_phone: str
    vehicle_id: str
    vehicle_name: str
    base_price: int
    discount: int = 0
    final_price: int
    request_note: str | None = None


class QuoteUpdateStatus(BaseModel):
    status: str  # "approved", "rejected", "pending"
    notes: str | None = None
    discount: int | None = None
    final_price: int | None = None


class QuoteResponse(QuoteCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


# --- Booking Schemas ---
class BookingCreate(BaseModel):
    customer_name: str
    customer_phone: str
    vehicle_id: str
    vehicle_name: str
    preferred_date: date
    preferred_time: str = "09:00"
    notes: str | None = None


class BookingUpdateStatus(BaseModel):
    status: str  # "confirmed", "completed", "cancelled", "pending"
    notes: str | None = None


class BookingResponse(BookingCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    created_at: datetime


# --- Customer Profile Schemas (Chân dung khách hàng 360° Tổng thể 1-1) ---
class CustomerProfileBase(BaseModel):
    lead_score: str = "WARM"
    lead_status: str = "NEW"
    all_interested_models: list[str] = Field(default_factory=list)
    customer_note: str | None = None


class CustomerProfileCreate(CustomerProfileBase):
    user_id: uuid.UUID


class CustomerProfileUpdate(BaseModel):
    lead_score: str | None = None
    lead_status: str | None = None
    all_interested_models: list[str] | None = None
    customer_note: str | None = None


class CustomerProfileResponse(CustomerProfileBase):
    model_config = ConfigDict(from_attributes=True)

    profile_id: uuid.UUID
    user_id: uuid.UUID
    account: UserResponse | None = None
    total_demands: int = 0
    total_quotes: int = 0
    total_test_drives: int = 0
    last_interaction_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --- Customer Demand Schemas (Lịch sử các đợt tìm xe 1-N) ---
class CustomerDemandBase(BaseModel):
    vehicle_type: str = "CAR"
    target_models: list[str] = Field(default_factory=list)
    budget_min: int | None = None
    budget_max: int | None = None
    usage_purpose: str | None = None
    battery_preference: str | None = None
    charging_condition: str | None = None
    demand_summary: str | None = None
    status: str = "ACTIVE"


class CustomerDemandCreate(CustomerDemandBase):
    user_id: uuid.UUID
    session_id: str | None = None


class CustomerDemandUpdate(BaseModel):
    vehicle_type: str | None = None
    target_models: list[str] | None = None
    budget_min: int | None = None
    budget_max: int | None = None
    usage_purpose: str | None = None
    battery_preference: str | None = None
    charging_condition: str | None = None
    demand_summary: str | None = None
    status: str | None = None


class CustomerDemandResponse(CustomerDemandBase):
    model_config = ConfigDict(from_attributes=True)

    demand_id: uuid.UUID
    user_id: uuid.UUID
    session_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CustomerProfileFull360Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile: CustomerProfileResponse
    demands: list[CustomerDemandResponse] = Field(default_factory=list)
    quotes: list[QuoteResponse] = Field(default_factory=list)
    test_drives: list[BookingResponse] = Field(default_factory=list)


