from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol
from uuid import UUID, uuid4

from src.domain.accounts import Account


class LeadScore(str, Enum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


class LeadStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    TEST_DRIVEN = "TEST_DRIVEN"
    QUOTED = "QUOTED"
    WON = "WON"
    LOST = "LOST"


@dataclass
class CustomerProfile:
    """Staff-facing CRM facts derived from a customer's own actions."""

    profile_id: UUID
    user_id: UUID
    lead_score: LeadScore = LeadScore.WARM
    lead_status: LeadStatus = LeadStatus.NEW
    all_interested_models: list[str] = field(default_factory=list)
    customer_note: str | None = None
    total_demands: int = 0
    total_quotes: int = 0
    total_test_drives: int = 0
    last_interaction_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    account: Account | None = None

    @classmethod
    def new_for(cls, user_id: UUID, now: datetime) -> CustomerProfile:
        return cls(profile_id=uuid4(), user_id=user_id, last_interaction_at=now)

    def record_quote(self, vehicle_name: str, now: datetime) -> None:
        self.total_quotes += 1
        self.lead_status = LeadStatus.QUOTED
        self.lead_score = LeadScore.HOT
        self._remember_model(vehicle_name)
        self.last_interaction_at = now

    def record_test_drive(self, vehicle_name: str, now: datetime) -> None:
        self.total_test_drives += 1
        self.lead_status = LeadStatus.TEST_DRIVEN
        self.lead_score = LeadScore.HOT
        self._remember_model(vehicle_name)
        self.last_interaction_at = now

    def _remember_model(self, vehicle_name: str) -> None:
        name = (vehicle_name or "").strip()
        if name and name not in self.all_interested_models:
            self.all_interested_models = [*self.all_interested_models, name]


@dataclass(frozen=True)
class CustomerProfileFilter:
    lead_score: LeadScore | None = None
    lead_status: LeadStatus | None = None
    search: str | None = None
    skip: int = 0
    limit: int = 50


class CustomerProfileRepository(Protocol):
    async def get(self, profile_id: UUID) -> CustomerProfile | None: ...

    async def get_by_user(self, user_id: UUID) -> CustomerProfile | None: ...

    async def list(self, criteria: CustomerProfileFilter) -> list[CustomerProfile]: ...

    async def add(self, profile: CustomerProfile) -> CustomerProfile: ...

    async def save(self, profile: CustomerProfile) -> CustomerProfile: ...
