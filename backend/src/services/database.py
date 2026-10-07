from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_settings

settings = get_settings()

connect_args = {}
db_url = settings.effective_database_url
if "sqlite" in db_url:
    connect_args["check_same_thread"] = False
else:
    connect_args["statement_cache_size"] = 0
    connect_args["prepared_statement_name_func"] = lambda *args: ""
    # All ORM and unqualified SQL in the application must resolve to public.
    connect_args["server_settings"] = {"search_path": "public"}

engine = create_async_engine(
    db_url,
    pool_size=5,
    max_overflow=5,
    pool_recycle=300,
    pool_pre_ping=True,
    connect_args=connect_args,
)


SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
