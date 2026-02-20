from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from compgraph.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=(settings.ENVIRONMENT == "dev"),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    connect_args={"ssl": "require"},
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
