import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Xác định gốc repository để tạo đường dẫn mặc định nhất quán khi chạy từ thư mục khác.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
# Các khóa bí mật mẫu không được phép dùng khi ứng dụng chạy production.
WEAK_SECRETS = {
    "change-this-development-secret",
    "change-this-development-secret-key",
    "replace-with-at-least-32-random-characters",
}


# Chuẩn hóa URL PostgreSQL từ các nhà cung cấp sang driver bất đồng bộ của SQLAlchemy.
def normalize_database_url(url: str) -> str:
    """Accept provider URLs such as postgres:// and select the async driver."""
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    return url


# Tập trung cấu hình ứng dụng; giá trị có thể được ghi đè bằng biến môi trường hoặc .env.
class Settings(BaseSettings):
    # Đọc cấu hình .env ở repository trước, rồi đến .env tương đối với thư mục chạy.
    model_config = SettingsConfigDict(
        env_file=(REPOSITORY_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Tên dịch vụ, môi trường chạy, địa chỉ bind, cổng API và mức ghi log.
    app_name: str = "VinFast Digital Showroom"
    app_env: Literal["development", "production", "test"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    api_prefix: str = "/api/v1"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Kết nối database và thông tin ký/xác minh access token.
    database_url: str = "sqlite+aiosqlite:///./vinfast.db"
    secret_key: str = "change-this-development-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60 * 24 * 7, ge=1)

    # Danh sách origin được phép gọi API từ trình duyệt, phân cách bằng dấu phẩy.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"

    # Runtime locations. Docker sets these explicitly (see backend/Dockerfile).
    static_dir: Path = REPOSITORY_ROOT / "static"
    seed_data_dir: Path = REPOSITORY_ROOT / "data" / "catalog"
    frontend_dist_dir: Path = REPOSITORY_ROOT / "frontend" / "dist"

    # Bật/tắt seed dữ liệu tham chiếu, tài khoản demo và giới hạn dung lượng upload.
    seed_reference_data: bool = True
    seed_demo_accounts: bool | None = None
    max_upload_bytes: int = Field(default=8 * 1024 * 1024, ge=1024)

    # Chuẩn hóa URL database ngay khi Pydantic nạp giá trị từ môi trường hoặc file .env.
    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    # Dùng thư mục tạm có thể ghi trên Vercel khi cấu hình SQLite cục bộ.
    @property
    def effective_database_url(self) -> str:
        if os.environ.get("VERCEL") and "sqlite" in self.database_url:
            return "sqlite+aiosqlite:////tmp/vinfast.db"
        return self.database_url

    # Tách chuỗi CORS thành danh sách origin đã bỏ khoảng trắng và phần tử rỗng.
    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # Mặc định chỉ nạp tài khoản demo ngoài production; cấu hình tường minh được ưu tiên.
    @property
    def should_seed_demo_accounts(self) -> bool:
        if self.seed_demo_accounts is not None:
            return self.seed_demo_accounts
        return self.app_env != "production"

    # Chặn cấu hình production dùng secret yếu hoặc cho phép CORS từ mọi origin.
    def validate_for_runtime(self) -> None:
        if self.app_env != "production":
            return
        if len(self.secret_key) < 32 or self.secret_key in WEAK_SECRETS:
            raise RuntimeError("SECRET_KEY must be a private random value of at least 32 characters in production")
        if "*" in self.cors_origins_list:
            raise RuntimeError("CORS_ORIGINS must list explicit origins in production")


# Dùng cache để chỉ tạo và nạp đối tượng cấu hình một lần trong tiến trình.
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
