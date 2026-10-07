"""FastAPI application entry point for the VinFast Digital Showroom."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text

from src.api.routes import router
from src.config import get_settings
from src.models.domain import Account, Base
from src.services.database import SessionLocal, engine
from src.services.security import hash_password
from src.services.vinfast_locations_service import seed_vinfast_locations_if_empty

settings = get_settings()
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = REPOSITORY_ROOT / "static"
FRONTEND_DIST = REPOSITORY_ROOT / "frontend" / "dist"


async def seed_demo_accounts() -> None:
    """Create stable demo accounts without overwriting user-managed data."""
    accounts = (
        ("admin@vinfast.vn", "0900000001", "admin123", "Quản trị viên VinFast", "admin"),
        ("staff@vinfast.vn", "0900000002", "staff123", "Tư vấn viên VinFast", "consultant"),
        ("customer@gmail.com", "0900000003", "123456", "Khách hàng Demo", "customer"),
    )
    async with SessionLocal() as session:
        for email, phone, password, full_name, role in accounts:
            existing = await session.scalar(select(Account).where(Account.email == email))
            if existing is None:
                session.add(
                    Account(
                        email=email,
                        phone=phone,
                        hashed_password=hash_password(password),
                        full_name=full_name,
                        role=role,
                        is_active=True,
                    )
                )
        await session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.app_env == "production" and (
        len(settings.secret_key) < 32
        or settings.secret_key in {
            "change-this-development-secret",
            "replace-with-at-least-32-random-characters",
        }
    ):
        raise RuntimeError("SECRET_KEY must be a private random value in production")
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    if settings.app_env != "production":
        await seed_demo_accounts()
    async with SessionLocal() as session:
        await seed_vinfast_locations_if_empty(session)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend showroom số VinFast: danh mục xe, báo giá, lịch lái thử, CRM "
        "và chat thời gian thực giữa khách hàng với nhân viên."
    ),
    version="2.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Authentication", "description": "Đăng ký, đăng nhập và quản lý tài khoản."},
        {"name": "Car catalog", "description": "Tra cứu và quản trị danh mục ô tô."},
        {"name": "Motorbike catalog", "description": "Tra cứu và quản trị danh mục xe máy điện."},
        {"name": "Quotes", "description": "Yêu cầu và xử lý báo giá."},
        {"name": "Test-drive bookings", "description": "Đặt và xử lý lịch lái thử."},
        {"name": "Human support chat", "description": "Hội thoại trực tiếp customer–staff qua REST/WebSocket."},
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# /api is used by the web client; /api/v1 remains the canonical versioned API.
app.include_router(router, prefix=settings.api_prefix)
app.include_router(router, prefix="/api", include_in_schema=False)


@app.get("/health", tags=["System"], summary="Kiểm tra trạng thái dịch vụ")
async def health() -> dict[str, str]:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        database = "connected"
    except Exception:
        database = "unavailable"
    return {"status": "ok", "database": database, "env": settings.app_env}


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        target = (FRONTEND_DIST / full_path).resolve()
        if target.is_file() and FRONTEND_DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")
