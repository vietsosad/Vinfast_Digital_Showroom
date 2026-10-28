from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol
from uuid import UUID

from src.domain.errors import ValidationError
from src.domain.workflow import ensure_transition


class QuoteStatus(str, Enum):
    PENDING = "pending"
    CONTACTED = "contacted"
    APPROVED = "approved"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


QUOTE_TRANSITIONS: dict[QuoteStatus, frozenset[QuoteStatus]] = {
    QuoteStatus.PENDING: frozenset(
        {QuoteStatus.CONTACTED, QuoteStatus.APPROVED, QuoteStatus.REJECTED, QuoteStatus.CANCELLED}
    ),
    QuoteStatus.CONTACTED: frozenset({QuoteStatus.APPROVED, QuoteStatus.REJECTED, QuoteStatus.CANCELLED}),
    QuoteStatus.APPROVED: frozenset({QuoteStatus.COMPLETED, QuoteStatus.CANCELLED}),
    QuoteStatus.COMPLETED: frozenset(),
    QuoteStatus.REJECTED: frozenset(),
    QuoteStatus.CANCELLED: frozenset(),
}


@dataclass
class Quote:
    id: UUID
    user_id: UUID | None
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

    def change_status(self, target: QuoteStatus) -> None:
        ensure_transition(self.status, target, QUOTE_TRANSITIONS, "báo giá")
        self.status = target

    def apply_discount(self, discount: int) -> None:
        if not 0 <= discount <= self.base_price:
            raise ValidationError("Chiết khấu phải nằm trong khoảng 0 đến giá niêm yết")
        self.discount = discount
        self.final_price = self.base_price - discount

    def apply_pricing(self, discount: int | None = None, final_price: int | None = None) -> None:
        """Staff pricing. ``base_price`` always stays the catalog list price.

        Without ``final_price`` the total is derived as base_price - discount. With it,
        staff quote a negotiated on-the-road total (fees included), recorded as given.
        """
        if final_price is None:
            if discount is not None:
                self.apply_discount(discount)
            return
        if final_price < 0 or (discount is not None and discount < 0):
            raise ValidationError("Giá chốt và chiết khấu không được âm")
        if discount is not None:
            self.discount = discount
        self.final_price = final_price


@dataclass(frozen=True)
class QuoteFilter:
    user_id: UUID | None = None
    email: str | None = None
    phone: str | None = None
    status: QuoteStatus | None = None


class QuoteRepository(Protocol):
    async def add(self, quote: Quote) -> Quote: ...

    async def get(self, quote_id: UUID) -> Quote | None: ...

    async def list(self, criteria: QuoteFilter) -> list[Quote]: ...

    async def save(self, quote: Quote) -> Quote: ...
