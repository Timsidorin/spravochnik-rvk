from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from .config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)


def _unicode_lower(value):
    return value.lower() if isinstance(value, str) else value


if engine.dialect.name == "sqlite":

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_on_connect(dbapi_connection, _record):
        # Встроенный lower() в SQLite понимает только ASCII, из-за чего
        # ilike-поиск по кириллице был регистрозависимым.
        dbapi_connection.create_function(
            "lower", 1, _unicode_lower, deterministic=True
        )
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
