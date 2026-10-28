from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# Cặp vĩ độ/kinh độ dùng để hiển thị địa điểm trên bản đồ.
class Coordinates(BaseModel):
    """Tọa độ địa lý của một địa điểm."""

    lat: float
    lng: float


# Hình dạng dữ liệu API trả về cho một địa điểm showroom, dịch vụ hoặc sạc.
class LocationResponse(BaseModel):
    """Thông tin một địa điểm, được trả về theo cấu trúc mà giao diện bản đồ sử dụng."""

    # Cho phép nhận tên thuộc tính Python và xuất tên trường theo alias cho frontend.
    model_config = ConfigDict(populate_by_name=True)

    # Định danh, tên, nhóm dịch vụ và nhãn hiển thị của địa điểm.
    id: str
    name: str
    types: list[str]
    type_label: str = Field(serialization_alias="typeLabel")
    # Thông tin địa chỉ hành chính; phường có thể chưa được xác định.
    province: str
    district: str
    ward: str | None = None
    address: str
    # Tọa độ phục vụ định vị và các thông tin liên hệ/vận hành có thể có.
    coordinates: Coordinates
    phone: str | None = None
    hotline_service: str | None = Field(None, serialization_alias="hotlineService")
    opening_hours: str = Field(serialization_alias="openingHours")
    charging_info: dict[str, Any] | None = Field(None, serialization_alias="chargingInfo")
    source: str


# Bao bọc danh sách địa điểm cùng trạng thái phản hồi và tổng số kết quả.
class LocationListResponse(BaseModel):
    """Phản hồi danh sách địa điểm kèm tổng số bản ghi."""

    status: str = "success"
    total: int
    data: list[LocationResponse]


# Thông tin xác nhận sau khi quản trị viên đồng bộ bộ dữ liệu địa điểm.
class LocationSyncResponse(BaseModel):
    """Kết quả đồng bộ dữ liệu địa điểm."""

    status: str = "success"
    message: str
    total_synced: int
