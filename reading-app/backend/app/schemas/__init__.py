import datetime
from pydantic import BaseModel


class BookBase(BaseModel):
    title: str
    author: str = ""
    publisher: str = ""
    isbn: str = ""
    description: str = ""
    category: str = ""
    subcategory: str = ""
    tags: str = ""


class CategoryItem(BaseModel):
    category: str
    subcategory: str
    count: int = 0


class BookOut(BookBase):
    id: int
    format: str
    file_path: str = ""
    file_size: int = 0
    page_count: int = 0
    word_count: int = 0
    cover_path: str = ""
    is_indexed: bool = False
    is_parsed: bool = False
    created_at: datetime.datetime
    progress: "ReadingProgressOut | None" = None
    shelf_status: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_exclude_rels(cls, obj):
        """Create BookOut from ORM object excluding lazy relationships."""
        data = {}
        for k in cls.model_fields:
            if k in ('progress', 'shelf_status'):
                continue
            try:
                val = getattr(obj, k)
                if hasattr(val, 'value'):
                    val = val.value
                data[k] = val
            except Exception:
                data[k] = None
        return cls(**data)


class BookListOut(BaseModel):
    total: int
    items: list[BookOut]


class ReadingProgressOut(BaseModel):
    id: int
    book_id: int
    current_page: int = 0
    current_chapter: str = ""
    current_cfi: str = ""
    total_pages: int = 0
    progress_percent: float = 0.0
    total_reading_seconds: int = 0
    last_read_at: datetime.datetime | None = None

    class Config:
        from_attributes = True


class ReadingProgressUpdate(BaseModel):
    current_page: int | None = None
    current_chapter: str | None = None
    current_cfi: str | None = None
    total_pages: int | None = None
    progress_percent: float | None = None
    reading_seconds_delta: int = 0


class HighlightOut(BaseModel):
    id: int
    book_id: int
    chapter: str = ""
    page: int = 0
    cfi: str = ""
    content: str
    note: str = ""
    color: str = "yellow"
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class HighlightCreate(BaseModel):
    book_id: int
    chapter: str = ""
    page: int = 0
    cfi: str = ""
    content: str
    note: str = ""
    color: str = "yellow"


class HighlightUpdate(BaseModel):
    note: str | None = None
    color: str | None = None


class ShelfUpdate(BaseModel):
    status: str
    rating: int | None = None


class ConversationOut(BaseModel):
    id: int
    title: str = ""
    model: str = ""
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    citations: list[dict] | None = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    message: str
    model: str = ""
    use_rag: bool = True
    book_ids: list[int] | None = None


class ChatResponse(BaseModel):
    conversation_id: int
    message: str
    citations: list[dict] = []


class BookSearchResult(BaseModel):
    id: int
    title: str
    author: str
    format: str
    cover_path: str
    snippet: str = ""
    match_page: int | None = None


class ScanProgress(BaseModel):
    total: int
    processed: int
    current_file: str = ""
    is_complete: bool = False
