import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.domain.identity import Role

# Cấu hình kiểm tra số điện thoại dùng chung cho các schema tài khoản.
PHONE_FIELD = Field(..., min_length=9, max_length=20, examples=["0912345678"])


class UserRegister(BaseModel):
    """Dữ liệu đăng ký công khai; tài khoản mới luôn có vai trò khách hàng."""

    # Email được kiểm tra định dạng; mật khẩu và họ tên có giới hạn độ dài.
    email: EmailStr
    phone: str = PHONE_FIELD
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=100)


class StaffCreate(UserRegister):
    # Dữ liệu tạo nhân viên kế thừa thông tin đăng ký, nhưng chỉ nhận vai trò nhân viên hoặc quản trị viên.
    role: Literal["consultant", "admin"] = "consultant"


class UserLogin(BaseModel):
    """Dữ liệu client gửi lên khi đăng nhập."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class ProfileUpdate(BaseModel):
    """Các trường tùy chọn để người dùng cập nhật hồ sơ cá nhân."""

    full_name: str | None = Field(None, min_length=2, max_length=100)
    phone: str | None = Field(None, min_length=9, max_length=20)
    password: str | None = Field(None, min_length=8, max_length=128, description="Bỏ trống để giữ mật khẩu hiện tại")

    @field_validator("password", mode="before")
    @classmethod
    def _blank_password_means_unchanged(cls, value):
        # Chuỗi rỗng hoặc chỉ có khoảng trắng được hiểu là không đổi mật khẩu.
        return None if isinstance(value, str) and not value.strip() else value


class UserUpdate(ProfileUpdate):
    """Dữ liệu cập nhật tài khoản; quyền sửa vai trò/trạng thái cần được kiểm tra ở tầng API/nghiệp vụ."""

    role: Role | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """Các thông tin tài khoản an toàn được phép trả về cho client."""

    # Cho phép tạo response trực tiếp từ thuộc tính của đối tượng ORM/domain.
    model_config = ConfigDict(from_attributes=True)

    # ID, thông tin liên hệ, vai trò và trạng thái tài khoản; không bao gồm mật khẩu/hash.
    id: uuid.UUID
    email: str
    phone: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime | None = None


class TokenResponse(BaseModel):
    """Cấu trúc phản hồi đăng nhập gồm token truy cập và thông tin tài khoản."""

    # Token dùng trong header Authorization: Bearer <access_token>.
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
