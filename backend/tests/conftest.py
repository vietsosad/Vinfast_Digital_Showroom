import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

TEST_ROOT = Path(tempfile.mkdtemp(prefix="p101-tests-"))
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(TEST_ROOT / 'test.db').as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
os.environ["STATIC_DIR"] = str(TEST_ROOT / "static")
os.environ["SEED_DATA_DIR"] = str(REPOSITORY_ROOT / "data" / "catalog")

from src.config import get_settings  # noqa: E402
from src.infrastructure.bootstrap import initialize_database  # noqa: E402
from src.infrastructure.database import engine  # noqa: E402
from src.infrastructure.orm import Base  # noqa: E402
from src.main import app  # noqa: E402
from tests.helpers import login  # noqa: E402

DEMO_CUSTOMER = ("customer@gmail.com", "123456")
DEMO_STAFF = ("staff@vinfast.vn", "staff123")
DEMO_ADMIN = ("admin@vinfast.vn", "admin123")


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest_asyncio.fixture(autouse=True)
async def fresh_database():
    """Every test starts from an identical, freshly seeded database."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await initialize_database(get_settings())
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest_asyncio.fixture
async def customer_headers(client):
    return await login(client, *DEMO_CUSTOMER)


@pytest_asyncio.fixture
async def staff_headers(client):
    return await login(client, *DEMO_STAFF)


@pytest_asyncio.fixture
async def admin_headers(client):
    return await login(client, *DEMO_ADMIN)


@pytest_asyncio.fixture
async def car(client):
    """An active car from the seeded catalog."""
    cars = (await client.get("/api/v1/cars")).json()
    return next(item for item in cars if item["is_active"] and item["list_price"] > 0)


@pytest.fixture
def anyio_backend():
    return "asyncio"
