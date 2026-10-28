from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import Depends, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.auth import AuthService
from src.application.bookings import BookingService
from src.application.catalog import CarCatalogService, MotorbikeCatalogService
from src.application.customer_profiles import CustomerProfileService
from src.application.locations import LocationService
from src.application.quotes import QuoteService
from src.application.support_chat import SupportChatService
from src.application.vehicle_media import VehicleMediaService
from src.config import get_settings
from src.domain.accounts import Account
from src.domain.errors import AuthenticationError
from src.domain.files import UploadedFile
from src.domain.identity import Role
from src.domain.unit_of_work import UnitOfWork
from src.infrastructure.database import database_is_available
from src.infrastructure.security import JwtTokenService, Pbkdf2PasswordHasher
from src.infrastructure.seed.locations_dataset import official_locations
from src.infrastructure.storage import LocalFileStorage
from src.infrastructure.unit_of_work import open_unit_of_work

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="JWT nhận từ POST /api/v1/auth/login. Dán giá trị access_token (không kèm chữ Bearer).",
)


# Các đối tượng stateless được cache để dùng chung giữa các request, tránh tạo lại không cần thiết.
@lru_cache(maxsize=1)
def get_password_hasher() -> Pbkdf2PasswordHasher:
    return Pbkdf2PasswordHasher()


# Tạo bộ xác thực token từ cấu hình ứng dụng; cấu hình chỉ được đọc khi cần lần đầu.
@lru_cache(maxsize=1)
def get_token_service() -> JwtTokenService:
    settings = get_settings()
    return JwtTokenService(settings.secret_key, settings.algorithm, settings.access_token_expire_minutes)


# Cung cấp adapter lưu tệp cục bộ dùng chung, với thư mục gốc từ cấu hình.
@lru_cache(maxsize=1)
def get_file_storage() -> LocalFileStorage:
    return LocalFileStorage(get_settings().static_dir)


# Mở một UnitOfWork cho mỗi request HTTP và đóng nó sau khi xử lý xong.
async def get_uow() -> AsyncIterator[UnitOfWork]:
    # Mỗi HTTP request nhận một unit of work riêng và luôn được đóng sau request.
    async with open_unit_of_work() as uow:
        yield uow


@asynccontextmanager
async def unit_of_work_scope() -> AsyncIterator[UnitOfWork]:
    """Unit of work for long-lived connections (WebSocket) outside request DI."""
    # WebSocket không chạy theo vòng đời dependency injection của HTTP request.
    async with open_unit_of_work() as uow:
        yield uow


# Kiểm tra khả năng kết nối database để health check hoặc startup có thể sử dụng.
async def check_database() -> bool:
    return await database_is_available()


# Lắp ghép AuthService với các adapter mật khẩu và token dùng chung.
def build_auth_service(uow: UnitOfWork) -> AuthService:
    return AuthService(uow, get_password_hasher(), get_token_service())


# Dependency FastAPI cung cấp AuthService cùng UnitOfWork trong phạm vi request.
def get_auth_service(uow: UnitOfWork = Depends(get_uow)) -> AuthService:
    return build_auth_service(uow)


# Tạo service danh mục ô tô với lưu trữ tệp và giới hạn upload từ cấu hình.
def get_car_service(uow: UnitOfWork = Depends(get_uow)) -> CarCatalogService:
    return CarCatalogService(uow, get_file_storage(), get_settings().max_upload_bytes)


# Tạo service danh mục xe máy với cùng chính sách lưu trữ và giới hạn upload.
def get_motorbike_service(uow: UnitOfWork = Depends(get_uow)) -> MotorbikeCatalogService:
    return MotorbikeCatalogService(uow, get_file_storage(), get_settings().max_upload_bytes)


# Cung cấp các application service gắn với UnitOfWork hiện tại.
def get_quote_service(uow: UnitOfWork = Depends(get_uow)) -> QuoteService:
    return QuoteService(uow)


def get_booking_service(uow: UnitOfWork = Depends(get_uow)) -> BookingService:
    return BookingService(uow)


def get_customer_profile_service(uow: UnitOfWork = Depends(get_uow)) -> CustomerProfileService:
    return CustomerProfileService(uow)


def get_location_service(uow: UnitOfWork = Depends(get_uow)) -> LocationService:
    return LocationService(uow, official_locations)


# Tạo service chat dùng chung quy tắc nghiệp vụ cho API HTTP và WebSocket.
def build_chat_service(uow: UnitOfWork) -> SupportChatService:
    return SupportChatService(uow)


# Dependency FastAPI cung cấp service chat trong phạm vi request HTTP.
def get_chat_service(uow: UnitOfWork = Depends(get_uow)) -> SupportChatService:
    return build_chat_service(uow)


# Tạo service quản lý media với storage và giới hạn kích thước upload.
def get_media_service(uow: UnitOfWork = Depends(get_uow)) -> VehicleMediaService:
    return VehicleMediaService(uow, get_file_storage(), get_settings().max_upload_bytes)


# Xác thực bearer token và trả về tài khoản; chuẩn hóa lỗi xác thực thành HTTP 401.
async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth: AuthService = Depends(get_auth_service),
) -> Account:
    """Single authentication gate shared by every protected endpoint."""
    # Tự kiểm tra thông tin xác thực để trả về lỗi 401 thống nhất khi thiếu token.
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chưa xác thực. Vui lòng đăng nhập",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return await auth.authenticate(credentials.credentials)
    except AuthenticationError as exc:
        # Chuyển lỗi nghiệp vụ xác thực thành phản hồi HTTP, giữ nguyên thông báo.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_roles(*roles: Role):
    """Role-based access control layered on top of ``get_current_user``."""
    # Đóng băng danh sách vai trò để kiểm tra quyền nhanh và không bị thay đổi ngoài ý muốn.
    allowed = frozenset(roles)

    async def role_checker(current_user: Account = Depends(get_current_user)) -> Account:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bạn không có quyền truy cập. Cần vai trò: {', '.join(sorted(r.value for r in allowed))}",
            )
        return current_user

    return role_checker


# Các dependency tiện dụng để bảo vệ route dành cho nhân viên hoặc quản trị viên.
require_staff = require_roles(Role.CONSULTANT, Role.ADMIN)
require_admin = require_roles(Role.ADMIN)


# Đọc tối đa giới hạn cho phép cộng một byte để phát hiện file quá dung lượng.
async def read_upload(upload: UploadFile, max_bytes: int | None = None) -> UploadedFile:
    """Read at most max_bytes + 1 so oversized files are rejected without buffering them fully."""
    limit = max_bytes or get_settings().max_upload_bytes
    # Đọc dư một byte để tầng xử lý phía sau nhận biết file vượt giới hạn.
    content = await upload.read(limit + 1)
    return UploadedFile(filename=upload.filename or "", content_type=upload.content_type, content=content)
