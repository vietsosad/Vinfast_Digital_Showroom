from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.customers import CustomerProfile, CustomerProfileFilter, LeadScore, LeadStatus
from src.domain.errors import NotFoundError, PermissionDeniedError, ValidationError
from src.domain.identity import Actor
from src.domain.unit_of_work import UnitOfWork

MAX_NOTE_LENGTH = 2_000


@dataclass(frozen=True)
class ProfileChanges:
    lead_score: LeadScore | None = None
    lead_status: LeadStatus | None = None
    all_interested_models: list[str] | None = None
    customer_note: str | None = None
    clear_note: bool = False


class CustomerProfileService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list_profiles(self, actor: Actor, criteria: CustomerProfileFilter) -> list[CustomerProfile]:
        self._require_staff(actor)
        return await self.uow.customer_profiles.list(criteria)

    async def get_profile(self, actor: Actor, profile_id: UUID) -> CustomerProfile:
        self._require_staff(actor)
        profile = await self.uow.customer_profiles.get(profile_id)
        if profile is None:
            raise NotFoundError("Không tìm thấy hồ sơ khách hàng")
        return profile

    async def get_own_profile(self, actor: Actor) -> CustomerProfile:
        profile = await self.uow.customer_profiles.get_by_user(actor.user_id)
        if profile is None:
            raise NotFoundError("Không tìm thấy hồ sơ khách hàng")
        return profile

    async def update_profile(self, actor: Actor, profile_id: UUID, changes: ProfileChanges) -> CustomerProfile:
        profile = await self.get_profile(actor, profile_id)
        if changes.lead_score is not None:
            profile.lead_score = changes.lead_score
        if changes.lead_status is not None:
            profile.lead_status = changes.lead_status
        if changes.all_interested_models is not None:
            models = [model.strip() for model in changes.all_interested_models if model and model.strip()]
            profile.all_interested_models = list(dict.fromkeys(models))
        if changes.customer_note is not None:
            note = changes.customer_note.strip()
            if len(note) > MAX_NOTE_LENGTH:
                raise ValidationError(f"Ghi chú tối đa {MAX_NOTE_LENGTH} ký tự")
            profile.customer_note = note or None
        elif changes.clear_note:
            profile.customer_note = None
        profile = await self.uow.customer_profiles.save(profile)
        await self.uow.commit()
        return profile

    @staticmethod
    def _require_staff(actor: Actor) -> None:
        if not actor.is_staff:
            raise PermissionDeniedError("Chỉ nhân viên được truy cập CRM")
