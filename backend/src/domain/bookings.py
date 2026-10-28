from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Protocol
from uuid import UUID

from src.domain.errors import ValidationError
from src.domain.workflow import ensure_transition

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
MAX_BOOKING_HORIZON_DAYS = 180
# Showrooms operate on Vietnam time (UTC+7, no daylight saving).
SHOWROOM_TIMEZONE = timezone(timedelta(hours=7))


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


BOOKING_TRANSITIONS: dict[BookingStatus, frozenset[BookingStatus]] = {
    BookingStatus.PENDING: frozenset({BookingStatus.CONFIRMED, BookingStatus.CANCELLED}),
    BookingStatus.CONFIRMED: frozenset({BookingStatus.COMPLETED, BookingStatus.CANCELLED}),
    BookingStatus.COMPLETED: frozenset(),
    BookingStatus.CANCELLED: frozenset(),
}


@dataclass
class Booking:
    id: UUID
    user_id: UUID | None
    customer_name: str
    customer_phone: str
    vehicle_id: str
    vehicle_name: str
    preferred_date: date
    preferred_time: str
    status: BookingStatus
    notes: str | None = None
    created_at: datetime | None = None

    def change_status(self, target: BookingStatus) -> None:
        ensure_transition(self.status, target, BOOKING_TRANSITIONS, "lịch lái thử")
        self.status = target


def showroom_today(now: datetime) -> date:
    return now.astimezone(SHOWROOM_TIMEZONE).date()


def validate_schedule(preferred_date: date, preferred_time: str, today: date) -> None:
    if not TIME_PATTERN.fullmatch(preferred_time or ""):
        raise ValidationError("Giờ lái thử phải theo định dạng HH:MM")
    if preferred_date < today:
        raise ValidationError("Ngày lái thử không được ở trong quá khứ")
    if preferred_date > today + timedelta(days=MAX_BOOKING_HORIZON_DAYS):
        raise ValidationError(f"Chỉ nhận đặt lịch trong vòng {MAX_BOOKING_HORIZON_DAYS} ngày")


@dataclass(frozen=True)
class BookingFilter:
    user_id: UUID | None = None
    phone: str | None = None
    status: BookingStatus | None = None


class BookingRepository(Protocol):
    async def add(self, booking: Booking) -> Booking: ...

    async def get(self, booking_id: UUID) -> Booking | None: ...

    async def list(self, criteria: BookingFilter) -> list[Booking]: ...

    async def save(self, booking: Booking) -> Booking: ...
