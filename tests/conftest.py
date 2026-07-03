import pytest
import pytest_asyncio
import uuid
import hashlib
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from src.main import app
from src.database import get_db
from src.config import get_settings
from src.models.auth import ApiKey, Role

@pytest_asyncio.fixture
async def engine():
    settings = get_settings()
    engine = create_async_engine(str(settings.database_url), pool_size=5, max_overflow=10)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(autouse=True)
async def clear_database(engine):
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE assets, asset_relationships, api_keys RESTART IDENTITY CASCADE;"))
    yield

@pytest_asyncio.fixture
async def db_session(engine):
    session_maker = async_sessionmaker(
        bind=engine, 
        expire_on_commit=False
    )
    async with session_maker() as session:
        yield session

@pytest_asyncio.fixture
async def raw_admin_api_key(db_session):
    raw_key = "test-admin-key"
    hashed_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    api_key = ApiKey(
        id=uuid.uuid4(),
        hashed_key=hashed_key,
        tenant_id=uuid.uuid4(),
        role=Role.admin.value
    )
    db_session.add(api_key)
    await db_session.commit()
    return raw_key

@pytest_asyncio.fixture
async def raw_viewer_api_key(db_session):
    raw_key = "test-viewer-key"
    hashed_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    api_key = ApiKey(
        id=uuid.uuid4(),
        hashed_key=hashed_key,
        tenant_id=uuid.uuid4(),
        role=Role.viewer.value
    )
    db_session.add(api_key)
    await db_session.commit()
    return raw_key

@pytest_asyncio.fixture
async def override_db(engine):
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async def _override():
        async with session_maker() as session:
            yield session
    return _override

@pytest_asyncio.fixture
async def client(override_db, raw_admin_api_key):
    app.dependency_overrides[get_db] = override_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers={"X-API-Key": raw_admin_api_key}) as ac:
        yield ac
        
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def viewer_client(override_db, raw_viewer_api_key):
    app.dependency_overrides[get_db] = override_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers={"X-API-Key": raw_viewer_api_key}) as ac:
        yield ac
        
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def unauth_client(override_db):
    app.dependency_overrides[get_db] = override_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()
