from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.quotes import Quote, QuoteFilter, QuoteStatus
from src.domain.workflow import parse_enum
from src.infrastructure.orm import QuoteRow


def _parse_uuid(value: str | None) -> UUID | None:
    try:
        return UUID(value) if value else None
    except ValueError:
        return None


def to_quote(row: QuoteRow) -> Quote:
    return Quote(
        id=row.id,
        user_id=_parse_uuid(row.user_id),
        customer_name=row.customer_name,
        customer_email=row.customer_email,
        customer_phone=row.customer_phone,
        vehicle_id=row.vehicle_id,
        vehicle_name=row.vehicle_name,
        base_price=row.base_price,
        discount=row.discount or 0,
        final_price=row.final_price,
        request_note=row.request_note,
        status=parse_enum(QuoteStatus, row.status, QuoteStatus.PENDING),
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyQuoteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, quote: Quote) -> Quote:
        row = QuoteRow(id=quote.id)
        self._copy(quote, row)
        self.session.add(row)
        await self.session.flush()
        return to_quote(row)

    async def get(self, quote_id: UUID) -> Quote | None:
        row = await self.session.get(QuoteRow, quote_id)
        return to_quote(row) if row else None

    async def list(self, criteria: QuoteFilter) -> list[Quote]:
        statement = select(QuoteRow)
        if criteria.user_id is not None:
            statement = statement.where(QuoteRow.user_id == str(criteria.user_id))
        if criteria.email:
            statement = statement.where(QuoteRow.customer_email.ilike(criteria.email.strip()))
        if criteria.phone:
            statement = statement.where(QuoteRow.customer_phone == criteria.phone.strip())
        if criteria.status is not None:
            statement = statement.where(QuoteRow.status == criteria.status.value)
        rows = await self.session.scalars(statement.order_by(QuoteRow.created_at.desc()))
        return [to_quote(row) for row in rows]

    async def save(self, quote: Quote) -> Quote:
        row = await self.session.get(QuoteRow, quote.id)
        if row is None:
            raise LookupError(f"Quote {quote.id} does not exist")
        self._copy(quote, row)
        await self.session.flush()
        return to_quote(row)

    @staticmethod
    def _copy(quote: Quote, row: QuoteRow) -> None:
        row.user_id = str(quote.user_id) if quote.user_id else None
        row.customer_name = quote.customer_name
        row.customer_email = quote.customer_email
        row.customer_phone = quote.customer_phone
        row.vehicle_id = quote.vehicle_id
        row.vehicle_name = quote.vehicle_name
        row.base_price = quote.base_price
        row.discount = quote.discount
        row.final_price = quote.final_price
        row.request_note = quote.request_note
        row.status = quote.status.value
        row.notes = quote.notes
