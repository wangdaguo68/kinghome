from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..core.database import get_db, sync_engine
from ..models.book import Book
from ..core.config import BOOK_LIBRARY_DIR
import json

router = APIRouter()


@router.get("/fulltext")
async def fulltext_search(
    q: str,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Full-text search across indexed book contents."""
    from sqlalchemy import text
    try:
        rows = (await db.execute(
            text("SELECT book_id, content, page_number, chapter_title FROM book_chunks WHERE book_chunks MATCH :query ORDER BY rank LIMIT :limit OFFSET :offset"),
            {"query": q, "limit": page_size, "offset": (page - 1) * page_size}
        )).fetchall()

        total = (await db.execute(
            text("SELECT COUNT(*) FROM book_chunks WHERE book_chunks MATCH :query"),
            {"query": q}
        )).scalar()

        book_ids = list(set(r[0] for r in rows))
        books_map = {}
        if book_ids:
            book_rows = (await db.execute(select(Book).where(Book.id.in_(book_ids)))).scalars().all()
            books_map = {b.id: b for b in book_rows}

        results = []
        for r in rows:
            b = books_map.get(r[0])
            if b:
                results.append({
                    "book_id": r[0],
                    "title": b.title,
                    "author": b.author or "",
                    "format": b.format.value if hasattr(b.format, 'value') else b.format,
                    "cover_path": b.cover_path or "",
                    "snippet": r[1][:300] if r[1] else "",
                    "match_page": r[2],
                    "chapter_title": r[3] or "",
                })
        return {"total": total, "items": results}
    except Exception:
        # FTS5 might not be set up yet, fall back to title search
        q_param = f"%{q}%"
        rows = (await db.execute(
            select(Book).where(
                (Book.title.contains(q)) | (Book.author.contains(q))
            ).limit(page_size).offset((page - 1) * page_size)
        )).scalars().all()
        total = (await db.execute(
            select(func.count(Book.id)).where(
                (Book.title.contains(q)) | (Book.author.contains(q))
            )
        )).scalar()
        results = [{"book_id": b.id, "title": b.title, "author": b.author or "",
                    "format": b.format.value if hasattr(b.format, 'value') else b.format,
                    "cover_path": b.cover_path or "", "snippet": "", "match_page": None,
                    "chapter_title": ""} for b in rows]
        return {"total": total, "items": results}
