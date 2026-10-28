from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.customers import CustomerProfile, CustomerProfileFilter, LeadScore, LeadStatus
from src.domain.workflow import parse_enum
from src.infrastructure.orm import AccountRow, CustomerProfileRow
from src.infrastructure.repositories.accounts import to_account


def to_profile(row: CustomerProfileRow) -> CustomerProfile:
    return CustomerProfile(
        profile_id=row.profile_id,
        user_id=row.user_id,
        lead_score=parse_enum(LeadScore, row.lead_score, LeadScore.WARM),
        lead_status=parse_enum(LeadStatus, row.lead_status, LeadStatus.NEW),
        all_interested_models=list(row.all_interested_models or []),
        customer_note=row.customer_note,
        total_demands=row.total_demands or 0,
        total_quotes=row.total_quotes or 0,
        total_test_drives=row.total_test_drives or 0,
        last_interaction_at=row.last_interaction_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        account=to_account(row.account) if row.account else None,
    )


class SqlAlchemyCustomerProfileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, profile_id: UUID) -> CustomerProfile | None:
        row = await self.session.scalar(select(CustomerProfileRow).where(CustomerProfileRow.profile_id == profile_id))
        return to_profile(row) if row else None

    async def get_by_user(self, user_id: UUID) -> CustomerProfile | None:
        row = await self._row_for_user(user_id)
        return to_profile(row) if row else None

    async def list(self, criteria: CustomerProfileFilter) -> list[CustomerProfile]:
        statement = select(CustomerProfileRow).join(AccountRow, CustomerProfileRow.user_id == AccountRow.user_id)
        if criteria.lead_score is not None:
            statement = statement.where(CustomerProfileRow.lead_score == criteria.lead_score.value)
        if criteria.lead_status is not None:
            statement = statement.where(CustomerProfileRow.lead_status == criteria.lead_status.value)
        if criteria.search:
            pattern = f"%{criteria.search.strip()}%"
            statement = statement.where(
                or_(AccountRow.full_name.ilike(pattern), AccountRow.phone.ilike(pattern), AccountRow.email.ilike(pattern))
            )
        statement = (
            statement.order_by(desc(CustomerProfileRow.last_interaction_at))
            .offset(criteria.skip)
            .limit(criteria.limit)
        )
        rows = (await self.session.scalars(statement)).unique()
        return [to_profile(row) for row in rows]

    async def add(self, profile: CustomerProfile) -> CustomerProfile:
        row = CustomerProfileRow(profile_id=profile.profile_id, user_id=profile.user_id)
        self._copy(profile, row)
        self.session.add(row)
        await self.session.flush()
        row = await self._row_for_user(profile.user_id)
        return to_profile(row)

    async def save(self, profile: CustomerProfile) -> CustomerProfile:
        row = await self._row_for_user(profile.user_id)
        if row is None:
            raise LookupError(f"Profile {profile.profile_id} does not exist")
        self._copy(profile, row)
        await self.session.flush()
        return to_profile(row)

    async def _row_for_user(self, user_id: UUID) -> CustomerProfileRow | None:
        return await self.session.scalar(select(CustomerProfileRow).where(CustomerProfileRow.user_id == user_id))

    @staticmethod
    def _copy(profile: CustomerProfile, row: CustomerProfileRow) -> None:
        row.lead_score = profile.lead_score.value
        row.lead_status = profile.lead_status.value
        row.all_interested_models = list(profile.all_interested_models)
        row.customer_note = profile.customer_note
        row.total_demands = profile.total_demands
        row.total_quotes = profile.total_quotes
        row.total_test_drives = profile.total_test_drives
        if profile.last_interaction_at is not None:
            row.last_interaction_at = profile.last_interaction_at
