"""Framework-independent business rules for catalog media."""

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


class MediaError(Exception):
    pass


class MediaNotFoundError(MediaError):
    pass


class MediaValidationError(MediaError):
    pass


class VehicleMediaService:
    def __init__(self, repository: VehicleMediaRepository):
        self.repository = repository

    async def list_media(self, vehicle_type: str, vehicle_id: UUID) -> list[MediaRecord]:
        self._validate_vehicle_type(vehicle_type)
        if not await self.repository.vehicle_exists(vehicle_type, vehicle_id):
            raise MediaNotFoundError("Không tìm thấy mẫu xe")
        return await self.repository.list_media(vehicle_type, vehicle_id)

    async def add_media(
        self, vehicle_type: str, vehicle_id: UUID, drafts: list[MediaDraft]
    ) -> list[MediaRecord]:
        self._validate_vehicle_type(vehicle_type)
        if not drafts or len(drafts) > 100:
            raise MediaValidationError("Mỗi lần nhập từ 1 đến 100 ảnh")
        if sum(1 for draft in drafts if draft.is_primary) > 1:
            raise MediaValidationError("Mỗi xe chỉ được có một ảnh chính")
        if not await self.repository.vehicle_exists(vehicle_type, vehicle_id):
            raise MediaNotFoundError("Không tìm thấy mẫu xe")

        existing = await self.repository.list_media(vehicle_type, vehicle_id)
        normalized = [self._normalize(draft) for draft in drafts]
        if not existing and not any(draft.is_primary for draft in normalized):
            first = normalized[0]
            normalized[0] = MediaDraft(**{**first.__dict__, "is_primary": True})
        return await self.repository.create_media(vehicle_type, vehicle_id, normalized)

    async def update_media(self, media_id: UUID, changes: dict) -> MediaRecord:
        allowed = {
            "media_type",
            "angle",
            "color_code",
            "alt_text",
            "sort_order",
            "is_primary",
            "source_url",
            "source_label",
        }
        clean = {key: value for key, value in changes.items() if key in allowed}
        if "media_type" in clean and clean["media_type"] not in MEDIA_TYPES:
            raise MediaValidationError("Loại media không hợp lệ")
        record = await self.repository.update_media(media_id, clean)
        if record is None:
            raise MediaNotFoundError("Không tìm thấy ảnh")
        return record

    async def delete_media(self, media_id: UUID) -> None:
        if not await self.repository.delete_media(media_id):
            raise MediaNotFoundError("Không tìm thấy ảnh")

    @staticmethod
    def _validate_vehicle_type(vehicle_type: str) -> None:
        if vehicle_type not in VEHICLE_TYPES:
            raise MediaValidationError("vehicle_type phải là car hoặc motorbike")

    @staticmethod
    def _normalize(draft: MediaDraft) -> MediaDraft:
        url = draft.url.strip()
        if not (url.startswith("/static/uploads/") or url.startswith("https://") or url.startswith("http://")):
            raise MediaValidationError("URL ảnh phải thuộc /static/uploads hoặc dùng HTTP(S)")
        if draft.media_type not in MEDIA_TYPES:
            raise MediaValidationError("Loại media không hợp lệ")
        if not -10_000 <= draft.sort_order <= 10_000:
            raise MediaValidationError("sort_order nằm ngoài giới hạn")
        return MediaDraft(
            url=url,
            media_type=draft.media_type,
            angle=(draft.angle or "").strip() or None,
            color_code=(draft.color_code or "").strip() or None,
            alt_text=(draft.alt_text or "").strip()[:255] or None,
            sort_order=draft.sort_order,
            is_primary=draft.is_primary,
            source_url=(draft.source_url or "").strip() or None,
            source_label=(draft.source_label or "").strip()[:120] or None,
            checksum=draft.checksum,
        )
