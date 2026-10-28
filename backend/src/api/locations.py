from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_location_service, require_admin
from src.api.schemas.common import errors
from src.api.schemas.locations import Coordinates, LocationListResponse, LocationResponse, LocationSyncResponse
from src.application.locations import LocationService
from src.domain.accounts import Account
from src.domain.locations import Location

router = APIRouter()


# Chuyển domain Location sang response schema, bao gồm tọa độ theo cấu trúc API.
def to_response(location: Location) -> LocationResponse:
    return LocationResponse(
        id=location.id,
        name=location.name,
        types=location.types,
        type_label=location.type_label,
        province=location.province,
        district=location.district,
        ward=location.ward,
        address=location.address,
        coordinates=Coordinates(lat=location.latitude, lng=location.longitude),
        phone=location.phone,
        hotline_service=location.hotline_service,
        opening_hours=location.opening_hours,
        charging_info=location.charging_info,
        source=location.source,
    )


# Trả danh sách địa điểm đã lọc theo loại nhu cầu, tỉnh/thành và từ khóa.
@router.get("", response_model=LocationListResponse, summary="Showroom, xưởng dịch vụ và trạm sạc")
async def list_locations(
    demand_type: str | None = Query(None, max_length=200, description="Lọc theo loại, ví dụ showroom_car,charging_car"),
    province: str | None = Query(None, max_length=100, description="Lọc theo tỉnh/thành phố"),
    search: str | None = Query(None, max_length=100, description="Tìm theo tên hoặc địa chỉ"),
    service: LocationService = Depends(get_location_service),
) -> LocationListResponse:
    # Giao việc lọc cho application service rồi chuyển từng kết quả sang schema phản hồi.
    locations = await service.list_locations(demand_type=demand_type, province=province, search=search)
    return LocationListResponse(total=len(locations), data=[to_response(location) for location in locations])


# Đồng bộ dataset địa điểm; dependency chỉ cho phép quản trị viên gọi endpoint này.
@router.post("/sync", response_model=LocationSyncResponse, summary="Nạp lại dataset địa điểm", responses=errors(401, 403))
async def sync_locations(
    current_user: Account = Depends(require_admin),
    service: LocationService = Depends(get_location_service),
) -> LocationSyncResponse:
    # Nhận số lượng bản ghi được đồng bộ và trả thông báo có cấu trúc cho client.
    total = await service.synchronize(current_user.actor)
    return LocationSyncResponse(message=f"Đã đồng bộ {total} địa điểm VinFast", total_synced=total)
