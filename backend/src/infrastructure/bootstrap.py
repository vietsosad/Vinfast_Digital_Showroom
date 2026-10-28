"""Start-up initialization: schema, migrations and idempotent seed data."""

from __future__ import annotations

import logging

from src.config import Settings
from src.infrastructure.database import SessionLocal, engine
from src.infrastructure.migrations import run_migrations
from src.infrastructure.orm import Base
from src.infrastructure.security import Pbkdf2PasswordHasher
from src.infrastructure.seed.accounts import seed_demo_accounts
from src.infrastructure.seed.catalog import seed_catalog_if_empty
from src.infrastructure.seed.locations_dataset import official_locations
from src.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)


# Tạo các bảng ORM còn thiếu rồi áp dụng migration bổ sung trên cùng kết nối.
async def create_schema() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(run_migrations)


# Chỉ nạp bộ dữ liệu địa điểm tham chiếu khi repository chưa có bản ghi nào.
async def seed_locations_if_empty() -> int:
    async with SessionLocal() as session:
        # Dùng UnitOfWork để thao tác repository và commit theo ranh giới transaction chuẩn.
        uow = SqlAlchemyUnitOfWork(session)
        if await uow.locations.count():
            return 0
        # Nạp dataset chính thức rồi lưu một lần; trả số địa điểm mới được thêm.
        total = await uow.locations.upsert_many(official_locations())
        await uow.commit()
        return total


# Thiết lập schema và nạp các nhóm dữ liệu được bật trong cấu hình ứng dụng.
async def initialize_database(settings: Settings) -> None:
    # Bảo đảm database sẵn sàng trước khi chạy các bước seed.
    await create_schema()
    # Tài khoản demo chỉ được seed theo chính sách môi trường/cấu hình.
    if settings.should_seed_demo_accounts:
        async with SessionLocal() as session:
            created = await seed_demo_accounts(session, Pbkdf2PasswordHasher())
        if created:
            logger.info("Seeded %d demo accounts", created)
    # Dữ liệu catalog và địa điểm tham chiếu có thể tắt độc lập qua cấu hình.
    if settings.seed_reference_data:
        async with SessionLocal() as session:
            inserted = await seed_catalog_if_empty(session, settings.seed_data_dir)
        if any(inserted.values()):
            logger.info("Seeded catalog: %s", inserted)
        locations = await seed_locations_if_empty()
        if locations:
            logger.info("Seeded %d showroom/charging locations", locations)


# Giải phóng connection pool khi ứng dụng dừng để đóng các kết nối database.
async def dispose_engine() -> None:
    await engine.dispose()
