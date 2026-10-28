"""Schemas for quotes, test-drive bookings and the CRM."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from src.api.schemas.auth import UserResponse
from src.domain.bookings import BookingStatus
from src.domain.customers import LeadScore, LeadStatus
from src.domain.quotes import QuoteStatus


class QuoteCreate(BaseModel):
    """Only the vehicle and a note are accepted; name and prices come from the catalog."""

    vehicle_id: uuid.UUID
    request_note: str | None = Field(None, max_length=1_000)


class QuoteReviewRequest(BaseModel):
    status: QuoteStatus
    notes: str | None = Field(None, max_length=2_000)
    discount: int | None = Field(None, ge=0, description="Không gửi final_price: final_price = base_price - discount")
    final_price: int | None = Field(None, ge=0, description="Giá chốt lăn bánh do nhân viên báo (đã gồm phí)")


class QuoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    customer_name: str
    customer_email: str | None
    customer_phone: str
    vehicle_id: str
    vehicle_name: str
    base_price: int
    discount: int
    final_price: int
    request_note: str | None
    status: QuoteStatus
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BookingCreate(BaseModel):
    """Customer identity is taken from the token, never from the body."""

    vehicle_id: uuid.UUID
    preferred_date: date
    preferred_time: str = Field("09:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$", examples=["09:30"])
    notes: str | None = Field(None, max_length=1_000)


class BookingStatusUpdate(BaseModel):
    status: BookingStatus
    notes: str | None = Field(None, max_length=1_000)


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    customer_name: str
    customer_phone: str
    vehicle_id: str
    vehicle_name: str
    preferred_date: date
    preferred_time: str
    status: BookingStatus
    notes: str | None = None
    created_at: datetime | None = None


class CustomerProfileUpdate(BaseModel):
    lead_score: LeadScore | None = None
    lead_status: LeadStatus | None = None
    all_interested_models: list[str] | None = Field(None, max_length=50)
    customer_note: str | None = Field(None, max_length=2_000)


class CustomerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile_id: uuid.UUID
    user_id: uuid.UUID
    lead_score: LeadScore
    lead_status: LeadStatus
    all_interested_models: list[str]
    customer_note: str | None = None
    account: UserResponse | None = None
    total_demands: int = 0
    total_quotes: int = 0
    total_test_drives: int = 0
    last_interaction_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
