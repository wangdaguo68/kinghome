from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from ..core.database import get_db
from ..models.book import Book, BookFormat, ReadingProgress
from ..schemas import BookOut, BookListOut, ReadingProgressOut, ReadingProgressUpdate
from ..services.book_service import scan_library, extract_metadata
from ..core.config import BOOK_LIBRARY_DIR
import os

router = APIRouter()


@router.get("", response_model=BookListOut)
async def list_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    format: str | None = None,
    category: str | None = None,
    status: str | None = None,
    search: str | None = None,
    sort: str = "updated_at",
    db: AsyncSession = Depends(get_db),
):
    q = select(Book)
    count_q = select(func.count(Book.id))

    if format:
        q = q.where(Book.format == format)
        count_q = count_q.where(Book.format == format)
    if category:
        q = q.where(or_(Book.category == category, Book.subcategory == category))
        count_q = count_q.where(or_(Book.category == category, Book.subcategory == category))
    if search:
        q = q.where(or_(Book.title.contains(search), Book.author.contains(search)))
        count_q = count_q.where(or_(Book.title.contains(search), Book.author.contains(search)))

    if status:
        from ..models.book import BookShelf
        q = q.join(BookShelf, Book.id == BookShelf.book_id, isouter=True).where(
            BookShelf.status == status
        )

    sort_col = getattr(Book, sort, Book.updated_at)
    q = q.order_by(sort_col.desc()).offset((page - 1) * page_size).limit(page_size)

    total = (await db.execute(count_q)).scalar()
    rows = (await db.execute(q)).scalars().all()

    # attach progress and shelf status
    book_ids = [r.id for r in rows]
    if book_ids:
        progress_q = select(ReadingProgress).where(ReadingProgress.book_id.in_(book_ids))
        progress_map = {p.book_id: p for p in (await db.execute(progress_q)).scalars().all()}
        from ..models.book import BookShelf, ReadingStatus
        shelf_q = select(BookShelf).where(BookShelf.book_id.in_(book_ids))
        shelf_map = {s.book_id: s for s in (await db.execute(shelf_q)).scalars().all()}
    else:
        progress_map = {}
        shelf_map = {}

    items = []
    for row in rows:
        out = BookOut.from_orm_exclude_rels(row)
        out.progress = ReadingProgressOut.model_validate(progress_map[row.id]) if row.id in progress_map else None
        if row.id in shelf_map:
            s = shelf_map[row.id].status
            out.shelf_status = s.value if hasattr(s, 'value') else s
        else:
            out.shelf_status = None
        items.append(out)

    return BookListOut(total=total, items=items)


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Book.category, Book.subcategory, func.count(Book.id))
        .where(Book.category != "").where(Book.category.isnot(None))
        .group_by(Book.category, Book.subcategory)
        .order_by(Book.category, Book.subcategory)
    )).all()
    categories_map: dict[str, dict] = {}
    for cat, subcat, count in rows:
        if cat not in categories_map:
            categories_map[cat] = {"category": cat, "subcategories": [], "total": 0}
        categories_map[cat]["subcategories"].append({"subcategory": subcat or "", "count": count})
        categories_map[cat]["total"] += count
    return list(categories_map.values())


@router.post("/classify")
async def classify_books(db: AsyncSession = Depends(get_db)):
    """Re-classify all books based on title keywords."""
    from ..services.classification_service import classify_title
    from sqlalchemy import update
    rows = (await db.execute(select(Book.id, Book.title, Book.category))).all()
    updated = 0
    for book_id, title, _ in rows:
        cat, subcat = classify_title(title)
        await db.execute(
            update(Book).where(Book.id == book_id).values(category=cat, subcategory=subcat)
        )
        updated += 1
    await db.commit()
    return {"ok": True, "updated": updated}


@router.get("/{book_id}", response_model=BookOut)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Book not found")
    out = BookOut.from_orm_exclude_rels(row)
    progress = (await db.execute(select(ReadingProgress).where(ReadingProgress.book_id == book_id))).scalar_one_or_none()
    out.progress = ReadingProgressOut.model_validate(progress) if progress else None
    return out


@router.get("/{book_id}/progress", response_model=ReadingProgressOut)
async def get_progress(book_id: int, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(ReadingProgress).where(ReadingProgress.book_id == book_id))).scalar_one_or_none()
    if not p:
        return ReadingProgressOut(id=0, book_id=book_id)
    return ReadingProgressOut.model_validate(p)


@router.put("/{book_id}/progress", response_model=ReadingProgressOut)
async def update_progress(book_id: int, data: ReadingProgressUpdate, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(ReadingProgress).where(ReadingProgress.book_id == book_id))).scalar_one_or_none()
    from datetime import datetime
    if not p:
        p = ReadingProgress(book_id=book_id, total_reading_seconds=0)
        db.add(p)
    if p.total_reading_seconds is None:
        p.total_reading_seconds = 0
    if data.current_page is not None:
        p.current_page = data.current_page
    if data.current_chapter is not None:
        p.current_chapter = data.current_chapter
    if data.current_cfi is not None:
        p.current_cfi = data.current_cfi
    if data.total_pages is not None:
        p.total_pages = data.total_pages
    if data.progress_percent is not None:
        p.progress_percent = data.progress_percent
    p.total_reading_seconds += data.reading_seconds_delta
    p.last_read_at = datetime.utcnow()
    await db.commit()
    await db.refresh(p)
    return ReadingProgressOut.model_validate(p)


@router.delete("/{book_id}")
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    book = (await db.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if not book:
        raise HTTPException(404, "Book not found")
    await db.delete(book)
    await db.commit()
    return {"ok": True}
