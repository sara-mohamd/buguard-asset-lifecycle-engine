import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.database import get_db
from src.config import get_settings

from sqlalchemy.future import select
from sqlalchemy import text

@pytest_asyncio.fixture
async def engine():
    settings = get_settings()
    engine = create_async_engine(str(settings.database_url))
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(engine):
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session

@pytest_asyncio.fixture(autouse=True)
async def clear_database(engine):
    """
    Clears the database before each test to ensure isolation.
    """
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE assets RESTART IDENTITY CASCADE;"))
    yield

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from src.main import app
from src.database import get_db

@pytest_asyncio.fixture
async def client(engine):
    """
    Returns an AsyncClient. The app's get_db dependency is overridden to use 
    the test engine, preventing cross-loop errors caused by the globally 
    initialized engine in src/database.py.
    """
    AsyncSessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async def override_get_db():
        async with AsyncSessionLocal() as session:
            yield session
            
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()
