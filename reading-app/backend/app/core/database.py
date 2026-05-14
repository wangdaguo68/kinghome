from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from .config import DATABASE_URL, SYNC_DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from sqlalchemy import create_engine
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Ensure indexes exist on existing databases
        await conn.run_sync(_create_indexes)


def _create_indexes(conn):
    """Create indexes that may be missing from older database versions."""
    indexes = [
        "CREATE INDEX IF NOT EXISTS ix_books_format ON books (format)",
        "CREATE INDEX IF NOT EXISTS ix_books_category ON books (category)",
        "CREATE INDEX IF NOT EXISTS ix_books_updated_at ON books (updated_at)",
        "CREATE INDEX IF NOT EXISTS ix_highlights_book_id ON highlights (book_id)",
    ]
    for sql in indexes:
        conn.exec_driver_sql(sql)
