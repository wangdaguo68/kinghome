import datetime
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.database import Base
import enum


class BookFormat(str, enum.Enum):
    PDF = "pdf"
    EPUB = "epub"
    MOBI = "mobi"


class ReadingStatus(str, enum.Enum):
    WANT_TO_READ = "want_to_read"
    READING = "reading"
    DONE = "done"


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    author: Mapped[str | None] = mapped_column(String(300), default="")
    publisher: Mapped[str | None] = mapped_column(String(300), default="")
    isbn: Mapped[str | None] = mapped_column(String(50), default="")
    cover_path: Mapped[str | None] = mapped_column(String(1000), default="")
    file_path: Mapped[str] = mapped_column(String(1000), unique=True)
    format: Mapped[BookFormat] = mapped_column(String(10), index=True)
    file_size: Mapped[int | None] = mapped_column(Integer, default=0)
    page_count: Mapped[int | None] = mapped_column(Integer, default=0)
    word_count: Mapped[int | None] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text, default="")
    category: Mapped[str | None] = mapped_column(String(200), default="", index=True)
    subcategory: Mapped[str | None] = mapped_column(String(200), default="")
    tags: Mapped[str | None] = mapped_column(String(500), default="")
    is_indexed: Mapped[bool] = mapped_column(default=False)
    is_parsed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow,
                                                           onupdate=datetime.datetime.utcnow, index=True)

    progress: Mapped["ReadingProgress | None"] = relationship(back_populates="book", uselist=False, lazy="raise")
    highlights: Mapped[list["Highlight"]] = relationship(back_populates="book", lazy="raise")


class ReadingProgress(Base):
    __tablename__ = "reading_progress"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), unique=True)
    current_page: Mapped[int] = mapped_column(Integer, default=0)
    current_chapter: Mapped[str | None] = mapped_column(String(500), default="")
    current_cfi: Mapped[str | None] = mapped_column(String(500), default="")
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    total_reading_seconds: Mapped[int] = mapped_column(Integer, default=0)
    last_read_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)

    book: Mapped["Book"] = relationship(back_populates="progress", lazy="raise")


class Highlight(Base):
    __tablename__ = "highlights"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    chapter: Mapped[str | None] = mapped_column(String(500), default="")
    page: Mapped[int | None] = mapped_column(Integer, default=0)
    cfi: Mapped[str | None] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(20), default="yellow")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    book: Mapped["Book"] = relationship(back_populates="highlights", lazy="raise")


class BookShelf(Base):
    __tablename__ = "bookshelf"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), unique=True)
    status: Mapped[ReadingStatus] = mapped_column(String(20), default=ReadingStatus.WANT_TO_READ)
    rating: Mapped[int | None] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
