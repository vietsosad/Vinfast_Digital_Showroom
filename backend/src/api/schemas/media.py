from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Dữ liệu tạo liên kết ảnh xe, gồm thông tin hiển thị và nguồn ảnh.
class MediaLinkCreate(BaseModel):
    url: str = Field(..., max_length=2_000)
    media_type: str = "exterior"
    angle: str | None = None
    color_code: str | None = None
    alt_text: str | None = None
    sort_order: int = Field(0, ge=-10_000, le=10_000)
    is_primary: bool = False
    source_url: str | None = None
    source_label: str | None = None


# Gói nhiều liên kết ảnh trong một yêu cầu, giới hạn từ 1 đến 100 ảnh.
class MediaBatchCreate(BaseModel):
    items: list[MediaLinkCreate] = Field(min_length=1, max_length=100)


# Các trường tùy chọn được phép cập nhật cho một ảnh xe.
class MediaUpdate(BaseModel):
    media_type: str | None = None
    angle: str | None = None
    color_code: str | None = None
    alt_text: str | None = None
    sort_order: int | None = Field(None, ge=-10_000, le=10_000)
    is_primary: bool | None = None
    source_url: str | None = None
    source_label: str | None = None


# Dữ liệu ảnh xe trả về cho client; hỗ trợ tạo response từ thuộc tính ORM.
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
