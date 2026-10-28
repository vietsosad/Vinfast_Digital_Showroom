from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from passlib.context import CryptContext

from src.domain.accounts import Account
from src.domain.errors import AuthenticationError


# Bộ băm mật khẩu dùng PBKDF2-SHA256, triển khai hợp đồng PasswordHasher của domain.
class Pbkdf2PasswordHasher:
    """PBKDF2-SHA256 via passlib (salted, 29k+ iterations, constant-time verify)."""

    # Khởi tạo Passlib với thuật toán PBKDF2-SHA256.
    def __init__(self) -> None:
        self._context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

    # Băm mật khẩu để lưu thay vì lưu mật khẩu nguyên bản.
    def hash(self, password: str) -> str:
        return self._context.hash(password)

    # Kiểm tra mật khẩu nhập vào có khớp với chuỗi băm đã lưu hay không.
    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._context.verify(password, password_hash)
        except (ValueError, TypeError):
            return False

# Dịch vụ tạo JWT và xác minh token để lấy ID tài khoản.
class JwtTokenService:
    # Nhận khóa bí mật, thuật toán ký và thời hạn hiệu lực của token.
    def __init__(self, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 60 * 24 * 7):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    # Tạo token mang ID, vai trò và thời điểm phát hành/hết hạn của tài khoản.
    def issue(self, account: Account) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(account.user_id),
            "role": account.role.value,
            "iat": now,
            "exp": now + timedelta(minutes=self.expire_minutes),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    # Xác minh token còn hạn và có đủ thông tin, rồi chuyển subject thành UUID tài khoản.
    def decode_subject(self, token: str) -> UUID:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"require": ["exp", "sub"]})
            return UUID(str(payload["sub"]))
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError("Token không hợp lệ hoặc đã hết hạn") from exc
