from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.domain.errors import ValidationError
from src.domain.identity import Actor, Role

PHONE_PATTERN = re.compile(r"^\+?\d{9,15}$")


@dataclass
class Account:
    user_id: UUID
    email: str
    phone: str
    full_name: str
    role: Role
    is_active: bool
    password_hash: str = field(repr=False)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def id(self) -> UUID:
        return self.user_id

    @property
    def actor(self) -> Actor:
        return Actor(user_id=self.user_id, role=self.role)


@dataclass(frozen=True)
class NewAccount:
    email: str
    phone: str
    full_name: str
    role: Role
    password_hash: str = field(repr=False)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_phone(phone: str) -> str:
    """Remove separators and validate a Vietnamese/international phone number."""
    cleaned = re.sub(r"[\s.\-()]", "", phone or "")
    if not PHONE_PATTERN.fullmatch(cleaned):
        raise ValidationError("Số điện thoại phải gồm 9–15 chữ số")
    return cleaned


def normalize_full_name(full_name: str) -> str:
    cleaned = " ".join((full_name or "").split())
    if not 2 <= len(cleaned) <= 100:
        raise ValidationError("Họ tên phải có từ 2 đến 100 ký tự")
    return cleaned


def validate_password(password: str) -> str:
    if len(password or "") < 8:
        raise ValidationError("Mật khẩu phải có ít nhất 8 ký tự")
    return password


class AccountRepository(Protocol):
    async def get(self, user_id: UUID) -> Account | None: ...

    async def get_by_email(self, email: str) -> Account | None: ...

    async def phone_in_use(self, phone: str, *, exclude_user_id: UUID | None = None) -> bool: ...

    async def list_all(self) -> list[Account]: ...

    async def add(self, account: NewAccount) -> Account: ...

    async def save(self, account: Account) -> Account: ...

    async def delete(self, user_id: UUID) -> None: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenService(Protocol):
    def issue(self, account: Account) -> str: ...

    def decode_subject(self, token: str) -> UUID:
        """Return the account id in a valid token or raise AuthenticationError."""
        ...
