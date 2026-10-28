from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Location:
    id: str
    name: str
    types: list[str]
    type_label: str
    province: str
    district: str
    address: str
    latitude: float
    longitude: float
    ward: str | None = None
    phone: str | None = None
    hotline_service: str | None = None
    opening_hours: str = "08:00 - 22:00 (Trạm sạc 24/7)"
    charging_info: dict[str, Any] | None = field(default=None)
    source: str = "vinfast_official"
    is_active: bool = True


class LocationRepository(Protocol):
    async def list_active(self, province: str | None = None, search: str | None = None) -> list[Location]: ...

    async def count(self) -> int: ...

    async def upsert_many(self, locations: list[Location]) -> int: ...
