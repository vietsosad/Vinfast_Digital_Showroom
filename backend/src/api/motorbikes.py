import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status

from src.api.dependencies import get_motorbike_service, read_upload, require_admin, require_staff
from src.api.schemas.catalog import MotorbikeCreate, MotorbikeResponse, MotorbikeUpdate
from src.api.schemas.common import MessageResponse, errors
from src.application.catalog import MotorbikeCatalogService
from src.domain.accounts import Account
from src.domain.catalog import Motorbike

router = APIRouter()


@router.get("", response_model=list[MotorbikeResponse], summary="Danh sách xe máy điện")
@router.get("/", response_model=list[MotorbikeResponse], include_in_schema=False)
async def list_motorbikes(
    category: str | None = None, service: MotorbikeCatalogService = Depends(get_motorbike_service)
) -> list[Motorbike]:
    return await service.list(category)


@router.get(
    "/{motorbike_id_or_code}",
    response_model=MotorbikeResponse,
    summary="Chi tiết xe máy điện theo id hoặc mã dòng xe",
    responses=errors(404),
)
async def get_motorbike(
    motorbike_id_or_code: str, service: MotorbikeCatalogService = Depends(get_motorbike_service)
) -> Motorbike:
    return await service.get(motorbike_id_or_code)


@router.post(
    "",
    response_model=MotorbikeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo xe máy điện (JSON)",
    responses=errors(401, 403),
)
async def create_motorbike(
    payload: MotorbikeCreate,
    _: Account = Depends(require_staff),
    service: MotorbikeCatalogService = Depends(get_motorbike_service),
) -> Motorbike:
    return await service.create(payload.model_dump())


@router.put(
    "/{motorbike_id}",
    response_model=MotorbikeResponse,
    summary="Cập nhật xe máy điện (JSON, partial)",
    responses=errors(401, 403, 404),
)
async def update_motorbike(
    motorbike_id: uuid.UUID,
    payload: MotorbikeUpdate,
    _: Account = Depends(require_staff),
    service: MotorbikeCatalogService = Depends(get_motorbike_service),
) -> Motorbike:
    return await service.update(motorbike_id, payload.model_dump(exclude_unset=True))


@router.post(
    "/{motorbike_id}/image",
    response_model=MotorbikeResponse,
    summary="Tải ảnh đại diện xe máy điện (multipart/form-data)",
    description="Ngoại lệ JSON duy nhất của catalog: nhận một tệp JPG/PNG/WebP/AVIF, kiểm tra kích thước, MIME và chữ ký tệp.",
    responses=errors(401, 403, 404, 413),
)
async def upload_motorbike_image(
    motorbike_id: uuid.UUID,
    image: UploadFile = File(...),
    _: Account = Depends(require_staff),
    service: MotorbikeCatalogService = Depends(get_motorbike_service),
) -> Motorbike:
    return await service.replace_image(motorbike_id, await read_upload(image))


@router.delete(
    "/{motorbike_id}", response_model=MessageResponse, summary="Xóa xe máy điện", responses=errors(401, 403, 404)
)
async def delete_motorbike(
    motorbike_id: uuid.UUID,
    _: Account = Depends(require_admin),
    service: MotorbikeCatalogService = Depends(get_motorbike_service),
) -> MessageResponse:
    motorbike = await service.delete(motorbike_id)
    return MessageResponse(message=f"Đã xóa thành công mẫu xe máy điện {motorbike.model_name}")
