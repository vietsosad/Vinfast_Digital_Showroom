from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.domain.errors import (
    AuthenticationError,
    ConflictError,
    DomainError,
    FileTooLargeError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

logger = logging.getLogger(__name__)

# Ánh xạ từng loại lỗi nghiệp vụ sang HTTP status; lỗi cụ thể được kiểm tra trước lỗi tổng quát.
STATUS_BY_ERROR: tuple[tuple[type[DomainError], int], ...] = (
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (AuthenticationError, status.HTTP_401_UNAUTHORIZED),
    (PermissionDeniedError, status.HTTP_403_FORBIDDEN),
    (ConflictError, status.HTTP_409_CONFLICT),
    (FileTooLargeError, 413),
    (ValidationError, 422),
)


# Chọn mã HTTP tương ứng với kiểu lỗi nghiệp vụ đã phát sinh.
def status_for(error: DomainError) -> int:
    # Giữ thứ tự ánh xạ từ lỗi cụ thể đến lỗi tổng quát để chọn đúng status.
    for error_type, code in STATUS_BY_ERROR:
        if isinstance(error, error_type):
            return code
    # Lỗi domain chưa có ánh xạ cụ thể được trả về dưới dạng yêu cầu không hợp lệ.
    return status.HTTP_400_BAD_REQUEST


# Đăng ký bộ xử lý tập trung để API trả lỗi nhất quán cho client.
def register_exception_handlers(app: FastAPI) -> None:
    # Chuyển lỗi nghiệp vụ thành mã HTTP và nội dung phản hồi phù hợp.
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        code = status_for(exc)
        # Bearer clients need this challenge header when authentication fails.
        headers = {"WWW-Authenticate": "Bearer"} if code == status.HTTP_401_UNAUTHORIZED else None
        return JSONResponse(status_code=code, content={"detail": exc.message}, headers=headers)

    # Ghi log lỗi bất ngờ để điều tra nhưng không gửi chi tiết nội bộ cho client.
    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Ghi đầy đủ lỗi phía máy chủ để chẩn đoán, nhưng không trả chi tiết nội bộ cho client.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Lỗi hệ thống không mong muốn"},
        )
