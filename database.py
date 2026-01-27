from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from settings import settings


class Base(DeclarativeBase):
    pass


# Use asyncpg driver for async operations
DATABASE_URL = settings.DATABASE_URL_asyncpg  # Fixed typo: asycpg → asyncpg


engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,  # Use DEBUG from settings
    poolclass=NullPool
)


async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncSession:
    """Get database session for FastAPI dependency injection"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            print("Database error:", e)
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables (optional - use Alembic instead)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
