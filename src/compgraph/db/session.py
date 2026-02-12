from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from compgraph.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=(settings.ENVIRONMENT == "dev"),
    pool_size=5,
    max_overflow=5,
    pool_recycle=300,
    pool_pre_ping=True,
    connect_args={"ssl": "require"},
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
