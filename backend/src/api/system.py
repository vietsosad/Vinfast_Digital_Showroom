from fastapi import APIRouter, Depends, Response, status

from src.api.dependencies import check_database
from src.api.schemas.common import HealthResponse
from src.config import get_settings

router = APIRouter()


# Endpoint kiểm tra tình trạng hoạt động của API và kết nối database.
@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Kiểm tra trạng thái dịch vụ và database",
    responses={503: {"model": HealthResponse, "description": "Database không truy cập được"}},
)
async def health(response: Response, database_ok: bool = Depends(check_database)) -> HealthResponse:
    # Lấy môi trường hiện tại để trả về cùng thông tin health check.
    env = get_settings().app_env
    if not database_ok:
        # Báo lỗi 503 khi database không khả dụng.
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unavailable", database="unavailable", env=env)
    # Trả về trạng thái thành công khi database kết nối được.
    return HealthResponse(status="ok", database="connected", env=env)
