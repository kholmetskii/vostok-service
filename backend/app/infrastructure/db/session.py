import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

db_url: str = os.getenv("DATABASE_URL", "")


if not db_url:
    raise RuntimeError("DATABASE_URL is not set")


engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
)

SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
