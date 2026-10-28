from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.application.catalog import find_vehicle
from src.application.clock import Clock, utc_now
from src.domain.accounts import Account
from src.domain.customers import CustomerProfile
from src.domain.errors import NotFoundError, PermissionDeniedError
from src.domain.identity import Actor
from src.domain.quotes import Quote, QuoteFilter, QuoteStatus
from src.domain.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class QuoteReview:
    status: QuoteStatus
    notes: str | None = None
    discount: int | None = None
    final_price: int | None = None


class QuoteService:
    def __init__(self, uow: UnitOfWork, clock: Clock = utc_now):
        self.uow = uow
        self.clock = clock

    async def request_quote(self, customer: Account, vehicle_id: UUID, request_note: str | None) -> Quote:
        """Create a quote whose name and price come from the catalog, plus its CRM update."""
        vehicle = await find_vehicle(self.uow, vehicle_id)
        quote = Quote(
            id=uuid4(),
            user_id=customer.user_id,
            customer_name=customer.full_name,
            customer_email=customer.email,
            customer_phone=customer.phone,
            vehicle_id=str(vehicle.vehicle_id),
            vehicle_name=vehicle.name,
            base_price=vehicle.list_price,
            discount=0,
            final_price=vehicle.list_price,
            request_note=(request_note or "").strip() or None,
            status=QuoteStatus.PENDING,
        )
        quote = await self.uow.quotes.add(quote)

        now = self.clock()
        profile = await self.uow.customer_profiles.get_by_user(customer.user_id)
        if profile is None:
            profile = CustomerProfile.new_for(customer.user_id, now)
            profile.record_quote(vehicle.name, now)
            await self.uow.customer_profiles.add(profile)
        else:
            profile.record_quote(vehicle.name, now)
            await self.uow.customer_profiles.save(profile)

        await self.uow.commit()
        return quote

    async def list_quotes(self, actor: Actor, criteria: QuoteFilter) -> list[Quote]:
        if not actor.is_staff:
            # Customers only ever see their own quotes, whatever filter they send.
            criteria = QuoteFilter(user_id=actor.user_id)
        return await self.uow.quotes.list(criteria)

    async def review(self, actor: Actor, quote_id: UUID, review: QuoteReview) -> Quote:
        if not actor.is_staff:
            raise PermissionDeniedError("Chỉ nhân viên được xử lý báo giá")
        quote = await self.uow.quotes.get(quote_id)
        if quote is None:
            raise NotFoundError("Không tìm thấy báo giá này")
        quote.change_status(review.status)
        quote.apply_pricing(discount=review.discount, final_price=review.final_price)
        if review.notes is not None:
            quote.notes = review.notes.strip() or None
        quote = await self.uow.quotes.save(quote)
        await self.uow.commit()
        return quote
