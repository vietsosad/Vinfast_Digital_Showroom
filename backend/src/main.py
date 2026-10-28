"""FastAPI application entry point for the VinFast Digital Showroom backend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.errors import register_exception_handlers
from src.api.routes import router
from src.api.system import router as system_router
from src.config import get_settings
from src.infrastructure.bootstrap import dispose_engine, initialize_database

# Nạp cấu hình một lần để dùng chung khi khởi tạo ứng dụng và middleware.
settings = get_settings()
# Thiết lập định dạng log theo mức được khai báo trong cấu hình môi trường.
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


# Quản lý vòng đời ứng dụng: kiểm tra cấu hình, khởi tạo tài nguyên và đóng kết nối.
@asynccontextmanager
async def lifespan(_: FastAPI):
    # Xác thực cấu hình production trước khi khởi động để tránh chạy với thiết lập không an toàn.
    settings.validate_for_runtime()
    # Tạo thư mục phục vụ tệp tĩnh nếu chưa có, sau đó khởi tạo database và dữ liệu cần thiết.
    settings.static_dir.mkdir(parents=True, exist_ok=True)
    await initialize_database(settings)
    yield
    # Giải phóng engine khi ứng dụng dừng.
    await dispose_engine()


# Khai báo metadata OpenAPI, phiên bản và lifecycle cho ứng dụng FastAPI.
app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend showroom số VinFast: danh mục xe, báo giá, lịch lái thử, CRM và chat thời gian thực "
        "giữa khách hàng với nhân viên.\n\n"
        "**Xác thực:** gọi `POST /api/v1/auth/login`, bấm **Authorize** và dán `access_token`.\n\n"
        "**Định dạng:** mọi request/response dùng JSON, trừ ba endpoint tải ảnh nhận `multipart/form-data`."
    ),
    version="2.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "System", "description": "Health check."},
        {"name": "Authentication", "description": "Đăng ký, đăng nhập và quản lý tài khoản."},
        {"name": "Car catalog", "description": "Tra cứu và quản trị danh mục ô tô."},
        {"name": "Motorbike catalog", "description": "Tra cứu và quản trị danh mục xe máy điện."},
        {"name": "Catalog media", "description": "Thư viện ảnh chuẩn hóa của từng mẫu xe."},
        {"name": "Quotes", "description": "Yêu cầu và xử lý báo giá."},
        {"name": "Test-drive bookings", "description": "Đặt và xử lý lịch lái thử."},
        {"name": "Customer CRM", "description": "Hồ sơ khách hàng cho nhân viên."},
        {"name": "Showrooms and charging", "description": "Mạng lưới showroom và trạm sạc."},
        {"name": "Ownership cost", "description": "Ước tính chi phí sở hữu."},
        {"name": "Human support chat", "description": "Hội thoại trực tiếp customer–staff qua REST/WebSocket."},
    ],
)
# Giới hạn các origin và header được phép gọi API từ trình duyệt.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    # Bearer tokens travel in the Authorization header, never in cookies.
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
# Chuyển lỗi nghiệp vụ và lỗi hệ thống thành phản hồi API nhất quán.
register_exception_handlers(app)

# Phục vụ ảnh/tệp tĩnh từ thư mục được cấu hình.
app.mount("/static", StaticFiles(directory=settings.static_dir, check_dir=False), name="static")
# Đăng ký health check và các router API chính.
app.include_router(system_router, tags=["System"])
# /api/v1 is the canonical versioned API; /api is a hidden alias used by the web client.
app.include_router(router, prefix=settings.api_prefix)
app.include_router(router, prefix="/api", include_in_schema=False)


FRONTEND_DIST = settings.frontend_dist_dir
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        # Phục vụ bundle JS/CSS đã build nếu frontend được triển khai cùng backend.
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    # Trả file frontend nếu tồn tại; các đường dẫn còn lại chuyển về index cho SPA routing.
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        target = (FRONTEND_DIST / full_path).resolve()
        if target.is_file() and FRONTEND_DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")
