from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.bookings import Booking, BookingFilter, BookingStatus
from src.domain.workflow import parse_enum
from src.infrastructure.orm import TestDriveBookingRow


def to_booking(row: TestDriveBookingRow) -> Booking:
    return Booking(
        id=row.id,
        user_id=row.user_id,
        customer_name=row.customer_name,
        customer_phone=row.customer_phone,
        vehicle_id=row.vehicle_id,
        vehicle_name=row.vehicle_name,
        preferred_date=row.preferred_date,
        preferred_time=row.preferred_time or "09:00",
        status=parse_enum(BookingStatus, row.status, BookingStatus.PENDING),
        notes=row.notes,
        created_at=row.created_at,
    )


class SqlAlchemyBookingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, booking: Booking) -> Booking:
        row = TestDriveBookingRow(id=booking.id)
        self._copy(booking, row)
        self.session.add(row)
        await self.session.flush()
        return to_booking(row)

    async def get(self, booking_id: UUID) -> Booking | None:
        row = await self.session.get(TestDriveBookingRow, booking_id)
        return to_booking(row) if row else None

    async def list(self, criteria: BookingFilter) -> list[Booking]:
        statement = select(TestDriveBookingRow)
        if criteria.user_id is not None:
            statement = statement.where(TestDriveBookingRow.user_id == criteria.user_id)
        if criteria.phone:
            statement = statement.where(TestDriveBookingRow.customer_phone == criteria.phone.strip())
        if criteria.status is not None:
            statement = statement.where(TestDriveBookingRow.status == criteria.status.value)
        rows = await self.session.scalars(statement.order_by(TestDriveBookingRow.created_at.desc()))
        return [to_booking(row) for row in rows]

    async def save(self, booking: Booking) -> Booking:
        row = await self.session.get(TestDriveBookingRow, booking.id)
        if row is None:
            raise LookupError(f"Booking {booking.id} does not exist")
        self._copy(booking, row)
        await self.session.flush()
        return to_booking(row)

    @staticmethod
    def _copy(booking: Booking, row: TestDriveBookingRow) -> None:
        row.user_id = booking.user_id
        row.customer_name = booking.customer_name
        row.customer_phone = booking.customer_phone
        row.vehicle_id = booking.vehicle_id
        row.vehicle_name = booking.vehicle_name
        row.preferred_date = booking.preferred_date
        row.preferred_time = booking.preferred_time
        row.status = booking.status.value
        row.notes = booking.notes
