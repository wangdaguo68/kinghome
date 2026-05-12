from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_db
from ..models.book import Highlight
from ..schemas import HighlightOut, HighlightCreate, HighlightUpdate

router = APIRouter()


@router.get("/book/{book_id}", response_model=list[HighlightOut])
async def get_highlights(book_id: int, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Highlight).where(Highlight.book_id == book_id).order_by(Highlight.created_at.desc())
    )).scalars().all()
    return [HighlightOut.model_validate(r) for r in rows]


@router.post("", response_model=HighlightOut)
async def create_highlight(data: HighlightCreate, db: AsyncSession = Depends(get_db)):
    h = Highlight(**data.model_dump())
    db.add(h)
    await db.commit()
    await db.refresh(h)
    return HighlightOut.model_validate(h)


@router.put("/{highlight_id}", response_model=HighlightOut)
async def update_highlight(highlight_id: int, data: HighlightUpdate, db: AsyncSession = Depends(get_db)):
    h = (await db.execute(select(Highlight).where(Highlight.id == highlight_id))).scalar_one_or_none()
    if not h:
        raise HTTPException(404, "Not found")
    if data.note is not None:
        h.note = data.note
    if data.color is not None:
        h.color = data.color
    await db.commit()
    await db.refresh(h)
    return HighlightOut.model_validate(h)


@router.delete("/{highlight_id}")
async def delete_highlight(highlight_id: int, db: AsyncSession = Depends(get_db)):
    h = (await db.execute(select(Highlight).where(Highlight.id == highlight_id))).scalar_one_or_none()
    if not h:
        raise HTTPException(404, "Not found")
    await db.delete(h)
    await db.commit()
    return {"ok": True}
