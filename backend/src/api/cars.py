import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status

from src.api.dependencies import get_car_service, read_upload, require_admin, require_staff
from src.api.schemas.catalog import CarCreate, CarResponse, CarUpdate
from src.api.schemas.common import MessageResponse, errors
from src.application.catalog import CarCatalogService
from src.domain.accounts import Account
from src.domain.catalog import Car

router = APIRouter()


@router.get("", response_model=list[CarResponse], summary="Danh sách ô tô")
@router.get("/", response_model=list[CarResponse], include_in_schema=False)
async def list_cars(category: str | None = None, service: CarCatalogService = Depends(get_car_service)) -> list[Car]:
    return await service.list(category)


@router.get("/{car_id_or_code}", response_model=CarResponse, summary="Chi tiết ô tô theo id hoặc mã dòng xe", responses=errors(404))
async def get_car(car_id_or_code: str, service: CarCatalogService = Depends(get_car_service)) -> Car:
    return await service.get(car_id_or_code)


@router.post(
    "",
    response_model=CarResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo ô tô (JSON)",
    responses=errors(401, 403),
)
async def create_car(
    payload: CarCreate,
    _: Account = Depends(require_staff),
    service: CarCatalogService = Depends(get_car_service),
) -> Car:
    return await service.create(payload.model_dump())


@router.put("/{car_id}", response_model=CarResponse, summary="Cập nhật ô tô (JSON, partial)", responses=errors(401, 403, 404))
async def update_car(
    car_id: uuid.UUID,
    payload: CarUpdate,
    _: Account = Depends(require_staff),
    service: CarCatalogService = Depends(get_car_service),
) -> Car:
    return await service.update(car_id, payload.model_dump(exclude_unset=True))


@router.post(
    "/{car_id}/image",
    response_model=CarResponse,
    summary="Tải ảnh đại diện ô tô (multipart/form-data)",
    description="Ngoại lệ JSON duy nhất của catalog: nhận một tệp JPG/PNG/WebP/AVIF, kiểm tra kích thước, MIME và chữ ký tệp.",
    responses=errors(401, 403, 404, 413),
)
async def upload_car_image(
    car_id: uuid.UUID,
    image: UploadFile = File(...),
    _: Account = Depends(require_staff),
    service: CarCatalogService = Depends(get_car_service),
) -> Car:
    return await service.replace_image(car_id, await read_upload(image))


@router.delete("/{car_id}", response_model=MessageResponse, summary="Xóa ô tô", responses=errors(401, 403, 404))
async def delete_car(
    car_id: uuid.UUID,
    _: Account = Depends(require_admin),
    service: CarCatalogService = Depends(get_car_service),
) -> MessageResponse:
    car = await service.delete(car_id)
    return MessageResponse(message=f"Đã xóa thành công mẫu xe {car.model_name}")
