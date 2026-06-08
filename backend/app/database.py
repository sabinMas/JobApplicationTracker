from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL configuration
# Supports both SQLite (development) and PostgreSQL (production)
# 
# SQLite:     sqlite+aiosqlite:///./data/app.db
# PostgreSQL: postgresql+asyncpg://user:pass@host:5432/dbname
#
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    # Default to SQLite for local development
    DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent.parent / "data")))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/app.db"

# Convert postgres:// to postgresql+asyncpg:// if needed (common with Heroku/Railway)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Engine configuration differs between SQLite and PostgreSQL
is_sqlite = "sqlite" in DATABASE_URL

engine_kwargs = {
    "echo": False,
}

if not is_sqlite:
    # PostgreSQL connection pool settings
    engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,  # Recycle connections every 30 min
        "pool_pre_ping": True,  # Verify connections before use
    })

engine = create_async_engine(DATABASE_URL, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
