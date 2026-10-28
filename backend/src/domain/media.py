from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

MEDIA_TYPES = {"hero", "exterior", "interior", "detail", "color", "document"}
VEHICLE_TYPES = {"car", "motorbike"}


@dataclass(frozen=True)
class MediaDraft:
    url: str
    media_type: str = "exterior"
    angle: str | None = None
    color_code: str | None = None
    alt_text: str | None = None
    sort_order: int = 0
    is_primary: bool = False
    source_url: str | None = None
    source_label: str | None = None
    checksum: str | None = None


@dataclass(frozen=True)
class MediaRecord(MediaDraft):
    media_id: UUID = UUID(int=0)
    vehicle_type: str = "car"
    vehicle_id: UUID = UUID(int=0)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class VehicleMediaRepository(Protocol):
    async def vehicle_exists(self, vehicle_type: str, vehicle_id: UUID) -> bool: ...

    async def list_media(self, vehicle_type: str, vehicle_id: UUID) -> list[MediaRecord]: ...

    async def create_media(
        self, vehicle_type: str, vehicle_id: UUID, drafts: list[MediaDraft]
    ) -> list[MediaRecord]: ...

    async def update_media(self, media_id: UUID, changes: dict) -> MediaRecord | None: ...

    async def delete_media(self, media_id: UUID) -> bool: ...
