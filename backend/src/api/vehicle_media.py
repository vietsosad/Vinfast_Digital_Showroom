from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from src.api.dependencies import get_media_service, read_upload, require_staff
from src.api.schemas.common import errors
from src.api.schemas.media import MediaBatchCreate, MediaResponse, MediaUpdate
from src.application.vehicle_media import VehicleMediaService
from src.domain.accounts import Account
from src.domain.media import MediaDraft, MediaRecord

router = APIRouter()


@router.get("/{vehicle_type}/{vehicle_id}", response_model=list[MediaResponse], summary="Thư viện ảnh của xe", responses=errors(404))
async def list_vehicle_media(
    vehicle_type: str,
    vehicle_id: UUID,
    service: VehicleMediaService = Depends(get_media_service),
) -> list[MediaRecord]:
    return await service.list_media(vehicle_type, vehicle_id)


@router.post(
    "/{vehicle_type}/{vehicle_id}/links",
    response_model=list[MediaResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Thêm ảnh bằng URL (JSON)",
    responses=errors(401, 403, 404),
)
async def add_vehicle_media_links(
    vehicle_type: str,
    vehicle_id: UUID,
    payload: MediaBatchCreate,
    _: Account = Depends(require_staff),
    service: VehicleMediaService = Depends(get_media_service),
) -> list[MediaRecord]:
    drafts = [MediaDraft(**item.model_dump()) for item in payload.items]
    return await service.add_media(vehicle_type, vehicle_id, drafts)


@router.post(
    "/{vehicle_type}/{vehicle_id}/upload",
    response_model=list[MediaResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Tải ảnh lên (multipart/form-data)",
    description="Tối đa 20 ảnh/lần; mỗi ảnh được kiểm tra kích thước, phần mở rộng, MIME và chữ ký tệp.",
    responses=errors(401, 403, 404, 413),
)
async def upload_vehicle_media(
    vehicle_type: str,
    vehicle_id: UUID,
    files: list[UploadFile] = File(...),
    media_type: str = Form("exterior"),
    angle: str | None = Form(None),
    color_code: str | None = Form(None),
    _: Account = Depends(require_staff),
    service: VehicleMediaService = Depends(get_media_service),
) -> list[MediaRecord]:
    uploads = [await read_upload(upload) for upload in files[:21]]
    return await service.upload_media(vehicle_type, vehicle_id, uploads, media_type, angle, color_code)


@router.put("/{media_id}", response_model=MediaResponse, summary="Cập nhật metadata ảnh", responses=errors(401, 403, 404))
async def update_vehicle_media(
    media_id: UUID,
    payload: MediaUpdate,
    _: Account = Depends(require_staff),
    service: VehicleMediaService = Depends(get_media_service),
) -> MediaRecord:
    return await service.update_media(media_id, payload.model_dump(exclude_unset=True))


@router.delete(
    "/{media_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa ảnh", responses=errors(401, 403, 404)
)
async def delete_vehicle_media(
    media_id: UUID,
    _: Account = Depends(require_staff),
    service: VehicleMediaService = Depends(get_media_service),
) -> None:
    await service.delete_media(media_id)
