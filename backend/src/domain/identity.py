from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class Role(str, Enum):
    CUSTOMER = "customer"
    CONSULTANT = "consultant"
    ADMIN = "admin"


STAFF_ROLES = frozenset({Role.CONSULTANT, Role.ADMIN})


@dataclass(frozen=True)
class Actor:
    """The authenticated principal on whose behalf a use case runs."""

    user_id: UUID
    role: Role

    @property
    def is_staff(self) -> bool:
        return self.role in STAFF_ROLES

    @property
    def is_admin(self) -> bool:
        return self.role is Role.ADMIN


def parse_role(value: str) -> Role:
    """Map a stored role string to the enum; unknown legacy values become customers."""
    try:
        return Role(value)
    except ValueError:
        return Role.CUSTOMER
