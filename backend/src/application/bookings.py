from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from src.application.catalog import find_vehicle
from src.application.clock import Clock, utc_now
from src.domain.accounts import Account
from src.domain.bookings import Booking, BookingFilter, BookingStatus, showroom_today, validate_schedule
from src.domain.customers import CustomerProfile
from src.domain.errors import NotFoundError, PermissionDeniedError
from src.domain.identity import Actor
from src.domain.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class BookingRequest:
    vehicle_id: UUID
    preferred_date: date
    preferred_time: str = "09:00"
    notes: str | None = None


class BookingService:
    def __init__(self, uow: UnitOfWork, clock: Clock = utc_now):
        self.uow = uow
        self.clock = clock

    async def book_test_drive(self, customer: Account, request: BookingRequest) -> Booking:
        """Book for the authenticated account; ownership is the account id, never a phone number."""
        now = self.clock()
        validate_schedule(request.preferred_date, request.preferred_time, showroom_today(now))
        vehicle = await find_vehicle(self.uow, request.vehicle_id)
        booking = await self.uow.bookings.add(
            Booking(
                id=uuid4(),
                user_id=customer.user_id,
                customer_name=customer.full_name,
                customer_phone=customer.phone,
                vehicle_id=str(vehicle.vehicle_id),
                vehicle_name=vehicle.name,
                preferred_date=request.preferred_date,
                preferred_time=request.preferred_time,
                status=BookingStatus.PENDING,
                notes=(request.notes or "").strip() or None,
            )
        )

        profile = await self.uow.customer_profiles.get_by_user(customer.user_id)
        if profile is None:
            profile = CustomerProfile.new_for(customer.user_id, now)
            profile.record_test_drive(vehicle.name, now)
            await self.uow.customer_profiles.add(profile)
        else:
            profile.record_test_drive(vehicle.name, now)
            await self.uow.customer_profiles.save(profile)

        await self.uow.commit()
        return booking

    async def list_bookings(self, actor: Actor, criteria: BookingFilter) -> list[Booking]:
        if not actor.is_staff:
            criteria = BookingFilter(user_id=actor.user_id)
        return await self.uow.bookings.list(criteria)

    async def change_status(
        self, actor: Actor, booking_id: UUID, status: BookingStatus, notes: str | None = None
    ) -> Booking:
        if not actor.is_staff:
            raise PermissionDeniedError("Chỉ nhân viên được xử lý lịch lái thử")
        booking = await self.uow.bookings.get(booking_id)
        if booking is None:
            raise NotFoundError("Không tìm thấy lịch hẹn lái thử này")
        booking.change_status(status)
        if notes is not None:
            booking.notes = notes.strip() or None
        booking = await self.uow.bookings.save(booking)
        await self.uow.commit()
        return booking
