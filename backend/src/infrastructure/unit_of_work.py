from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import SessionLocal
from src.infrastructure.repositories.accounts import SqlAlchemyAccountRepository
from src.infrastructure.repositories.bookings import SqlAlchemyBookingRepository
from src.infrastructure.repositories.catalog import SqlAlchemyCarRepository, SqlAlchemyMotorbikeRepository
from src.infrastructure.repositories.customer_profiles import SqlAlchemyCustomerProfileRepository
from src.infrastructure.repositories.locations import SqlAlchemyLocationRepository
from src.infrastructure.repositories.quotes import SqlAlchemyQuoteRepository
from src.infrastructure.repositories.support_chat import SqlAlchemyConversationRepository
from src.infrastructure.repositories.vehicle_media import SqlAlchemyVehicleMediaRepository


class SqlAlchemyUnitOfWork:
    """All repositories share one AsyncSession, i.e. one database transaction."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.accounts = SqlAlchemyAccountRepository(session)
        self.customer_profiles = SqlAlchemyCustomerProfileRepository(session)
        self.cars = SqlAlchemyCarRepository(session)
        self.motorbikes = SqlAlchemyMotorbikeRepository(session)
        self.quotes = SqlAlchemyQuoteRepository(session)
        self.bookings = SqlAlchemyBookingRepository(session)
        self.locations = SqlAlchemyLocationRepository(session)
        self.conversations = SqlAlchemyConversationRepository(session)
        self.media = SqlAlchemyVehicleMediaRepository(session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


@asynccontextmanager
async def open_unit_of_work() -> AsyncIterator[SqlAlchemyUnitOfWork]:
    async with SessionLocal() as session:
        uow = SqlAlchemyUnitOfWork(session)
        try:
            yield uow
        except BaseException:
            await session.rollback()
            raise
