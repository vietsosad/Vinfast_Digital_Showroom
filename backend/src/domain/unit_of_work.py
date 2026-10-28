from __future__ import annotations

from typing import Protocol

from src.domain.accounts import AccountRepository
from src.domain.bookings import BookingRepository
from src.domain.catalog import CarRepository, MotorbikeRepository
from src.domain.chat import ConversationRepository
from src.domain.customers import CustomerProfileRepository
from src.domain.locations import LocationRepository
from src.domain.media import VehicleMediaRepository
from src.domain.quotes import QuoteRepository


class UnitOfWork(Protocol):
    """One business transaction spanning every repository it touches.

    Repositories stage changes; only the use case decides when to commit, so a
    quote and its CRM side effects either persist together or not at all.
    """

    accounts: AccountRepository
    customer_profiles: CustomerProfileRepository
    cars: CarRepository
    motorbikes: MotorbikeRepository
    quotes: QuoteRepository
    bookings: BookingRepository
    locations: LocationRepository
    conversations: ConversationRepository
    media: VehicleMediaRepository

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
