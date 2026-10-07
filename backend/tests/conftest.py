import os
import sys
import tempfile

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

TEST_DB_PATH = os.path.join(tempfile.gettempdir(), f"p101-tests-{os.getpid()}.db")
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.replace(os.sep, '/')}"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"

from src.main import app, seed_demo_accounts
from src.models.domain import Base
from src.services.database import engine


@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await seed_demo_accounts()
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture
def anyio_backend():
    return "asyncio"
