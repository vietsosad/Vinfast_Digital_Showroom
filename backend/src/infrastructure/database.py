from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import Settings, get_settings


def build_engine(settings: Settings) -> AsyncEngine:
    url = settings.effective_database_url
    options: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False, "timeout": 30}
        if settings.app_env == "test":
            # Tests run many short event loops; never share pooled connections between them.
            options["poolclass"] = NullPool
    else:
        options.update(pool_size=5, max_overflow=5, pool_recycle=300)
        options["connect_args"] = {
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda *args: "",
            "server_settings": {"search_path": "public"},
        }

    engine = create_async_engine(url, **options)

    if url.startswith("sqlite"):

        @event.listens_for(engine.sync_engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _record):  # pragma: no cover - driver hook
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = build_engine(get_settings())
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def database_is_available() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
