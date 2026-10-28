from pydantic import BaseModel


class MessageResponse(BaseModel):
    """Phản hồi thành công đơn giản, chứa thông điệp cho client."""

    message: str


class ErrorResponse(BaseModel):
    """Cấu trúc phản hồi lỗi dùng chung cho API."""

    detail: str


class HealthResponse(BaseModel):
    """Thông tin trạng thái ứng dụng và kết nối cơ sở dữ liệu."""

    status: str
    database: str
    env: str


# Ánh xạ các mã HTTP thường dùng sang schema và mô tả trong tài liệu API.
ERROR_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Thiếu, sai hoặc hết hạn token"},
    403: {"model": ErrorResponse, "description": "Đã đăng nhập nhưng không đủ quyền"},
    404: {"model": ErrorResponse, "description": "Không tìm thấy tài nguyên"},
    409: {"model": ErrorResponse, "description": "Xung đột dữ liệu hoặc chuyển trạng thái không hợp lệ"},
    413: {"model": ErrorResponse, "description": "Tệp vượt quá giới hạn kích thước"},
}


def errors(*codes: int) -> dict:
    """Tạo danh sách phản hồi lỗi OpenAPI từ các mã HTTP được chỉ định."""
    return {code: ERROR_RESPONSES[code] for code in codes}
