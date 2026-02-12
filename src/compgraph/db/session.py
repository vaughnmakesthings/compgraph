from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from compgraph.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=(settings.ENVIRONMENT == "dev"))
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
