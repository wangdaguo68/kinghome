from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_db
from ..models.book import BookShelf, ReadingStatus, Book
from ..schemas import ShelfUpdate, BookOut

router = APIRouter()


@router.get("")
async def get_shelf(status: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(BookShelf)
    if status:
        q = q.where(BookShelf.status == status)
    q = q.order_by(BookShelf.added_at.desc())
    rows = (await db.execute(q)).scalars().all()
    book_ids = [r.book_id for r in rows]
    books_map = {}
    if book_ids:
        book_rows = (await db.execute(select(Book).where(Book.id.in_(book_ids)))).scalars().all()
        books_map = {b.id: b for b in book_rows}
    result = []
    for r in rows:
        b = books_map.get(r.book_id)
        if b:
            status = r.status
            if hasattr(status, 'value'):
                status = status.value
            result.append({
                "shelf_id": r.id,
                "status": status,
                "rating": r.rating,
                "added_at": r.added_at.isoformat(),
                "book": BookOut.from_orm_exclude_rels(b),
            })
    return result


@router.post("/{book_id}")
async def add_to_shelf(book_id: int, data: ShelfUpdate, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(BookShelf).where(BookShelf.book_id == book_id))).scalar_one_or_none()
    if existing:
        existing.status = ReadingStatus(data.status)
        if data.rating is not None:
            existing.rating = data.rating
    else:
        s = BookShelf(book_id=book_id, status=ReadingStatus(data.status), rating=data.rating)
        db.add(s)
    await db.commit()
    return {"ok": True}


@router.delete("/{book_id}")
async def remove_from_shelf(book_id: int, db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(BookShelf).where(BookShelf.book_id == book_id))).scalar_one_or_none()
    if s:
        await db.delete(s)
        await db.commit()
    return {"ok": True}
