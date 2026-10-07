from __future__ import annotations

import hashlib
import re
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.domain import Account
from src.repositories.vehicle_media import SqlAlchemyVehicleMediaRepository
from src.services.database import get_db
from src.services.security import require_roles
from src.services.vehicle_media import (
    MediaDraft,
    MediaNotFoundError,
    MediaRecord,
    MediaValidationError,
    VehicleMediaService,
)

router = APIRouter()
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
UPLOAD_ROOT = REPOSITORY_ROOT / "static" / "uploads"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
MAX_FILE_BYTES = 8 * 1024 * 1024


class MediaLinkCreate(BaseModel):
    url: str
    media_type: str = "exterior"
    angle: str | None = None
    color_code: str | None = None
    alt_text: str | None = None
    sort_order: int = Field(0, ge=-10_000, le=10_000)
    is_primary: bool = False
    source_url: str | None = None
    source_label: str | None = None


class MediaBatchCreate(BaseModel):
    items: list[MediaLinkCreate] = Field(min_length=1, max_length=100)


class MediaUpdate(BaseModel):
    media_type: str | None = None
    angle: str | None = None
    color_code: str | None = None
    alt_text: str | None = None
    sort_order: int | None = Field(None, ge=-10_000, le=10_000)
    is_primary: bool | None = None
    source_url: str | None = None
    source_label: str | None = None


class MediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    media_id: UUID
    vehicle_type: str
    vehicle_id: UUID
    url: str
    media_type: str
    angle: str | None
    color_code: str | None
    alt_text: str | None
    sort_order: int
    is_primary: bool
    source_url: str | None
    source_label: str | None
    checksum: str | None


def get_service(db: AsyncSession = Depends(get_db)) -> VehicleMediaService:
    return VehicleMediaService(SqlAlchemyVehicleMediaRepository(db))


def raise_media_error(exc: Exception) -> HTTPException:
    if isinstance(exc, MediaNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, MediaValidationError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Không thể xử lý thư viện ảnh")


@router.get("/{vehicle_type}/{vehicle_id}", response_model=list[MediaResponse])
async def list_vehicle_media(
    vehicle_type: str,
    vehicle_id: UUID,
    service: VehicleMediaService = Depends(get_service),
) -> list[MediaRecord]:
    try:
        return await service.list_media(vehicle_type, vehicle_id)
    except Exception as exc:
        raise raise_media_error(exc) from exc


@router.post(
    "/{vehicle_type}/{vehicle_id}/links",
    response_model=list[MediaResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_vehicle_media_links(
    vehicle_type: str,
    vehicle_id: UUID,
    payload: MediaBatchCreate,
    _: Account = Depends(require_roles(["admin", "consultant"])),
    service: VehicleMediaService = Depends(get_service),
) -> list[MediaRecord]:
    try:
        return await service.add_media(
            vehicle_type,
            vehicle_id,
            [MediaDraft(**item.model_dump()) for item in payload.items],
        )
    except Exception as exc:
        raise raise_media_error(exc) from exc


@router.post(
    "/{vehicle_type}/{vehicle_id}/upload",
    response_model=list[MediaResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_vehicle_media(
    vehicle_type: str,
    vehicle_id: UUID,
    files: list[UploadFile] = File(...),
    media_type: str = Form("exterior"),
    angle: str | None = Form(None),
    color_code: str | None = Form(None),
    _: Account = Depends(require_roles(["admin", "consultant"])),
    service: VehicleMediaService = Depends(get_service),
) -> list[MediaRecord]:
    if not 1 <= len(files) <= 20:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Mỗi lần tải tối đa 20 ảnh")
    folder_name = "cars" if vehicle_type == "car" else "motorbikes"
    target_dir = UPLOAD_ROOT / folder_name / "gallery" / str(vehicle_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    drafts: list[MediaDraft] = []

    for index, upload in enumerate(files):
        extension = Path(upload.filename or "").suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Chỉ hỗ trợ JPG, PNG, WebP hoặc AVIF")
        content = await upload.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Mỗi ảnh tối đa 8 MB")
        safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(upload.filename or "image").stem).strip("-")
        filename = f"{safe_stem or 'image'}-{uuid4().hex[:10]}{extension}"
        target = target_dir / filename
        target.write_bytes(content)
        drafts.append(
            MediaDraft(
                url=f"/static/uploads/{folder_name}/gallery/{vehicle_id}/{filename}",
                media_type=media_type,
                angle=angle,
                color_code=color_code,
                sort_order=index,
                checksum=hashlib.sha256(content).hexdigest(),
            )
        )

    try:
        return await service.add_media(vehicle_type, vehicle_id, drafts)
    except Exception as exc:
        raise raise_media_error(exc) from exc


@router.put("/{media_id}", response_model=MediaResponse)
async def update_vehicle_media(
    media_id: UUID,
    payload: MediaUpdate,
    _: Account = Depends(require_roles(["admin", "consultant"])),
    service: VehicleMediaService = Depends(get_service),
) -> MediaRecord:
    try:
        return await service.update_media(media_id, payload.model_dump(exclude_unset=True))
    except Exception as exc:
        raise raise_media_error(exc) from exc


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle_media(
    media_id: UUID,
    _: Account = Depends(require_roles(["admin", "consultant"])),
    service: VehicleMediaService = Depends(get_service),
) -> None:
    try:
        await service.delete_media(media_id)
    except Exception as exc:
        raise raise_media_error(exc) from exc
