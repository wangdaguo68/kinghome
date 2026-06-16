import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_db
from ..models.book import Book
from ..services.reader_service import (
    convert_epub_to_html, convert_pdf_to_html, get_book_toc,
    get_epub_chapter_html, get_chapter_content,
)
from ..core.config import CACHE_DIR

router = APIRouter()

MIME_TYPES = {"epub": "application/epub+zip", "pdf": "application/pdf", "mobi": "application/x-mobipocket-ebook"}


@router.get("/{book_id}/file")
async def get_book_file(book_id: int, db: AsyncSession = Depends(get_db)):
    book = (await db.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if not book:
        raise HTTPException(404, "Book not found")
    if not os.path.exists(book.file_path):
        raise HTTPException(404, "File not found on disk")
    fmt = book.format.value if hasattr(book.format, 'value') else book.format
    media_type = MIME_TYPES.get(fmt, "application/octet-stream")
    return FileResponse(book.file_path, media_type=media_type)


@router.get("/{book_id}/content")
async def get_book_content(book_id: int, db: AsyncSession = Depends(get_db)):
    book = (await db.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if not book:
        raise HTTPException(404, "Book not found")
    fmt = book.format.value if hasattr(book.format, 'value') else book.format
    try:
        if fmt == "epub":
            return convert_epub_to_html(book.file_path, book.id)
        elif fmt == "pdf":
            return convert_pdf_to_html(book.file_path, book.id)
        elif fmt == "mobi":
            from ..services.reader_service import convert_mobi_to_text
            text = convert_mobi_to_text(book.file_path)
            return {"chapters": [{"index": 0, "title": book.title or "MOBI Book"}], "content": text, "format": "text"}
        else:
            raise HTTPException(400, f"Unsupported format: {fmt}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to read book: {str(e)}")


@router.get("/{book_id}/toc")
async def get_toc(book_id: int, db: AsyncSession = Depends(get_db)):
    book = (await db.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if not book:
        raise HTTPException(404, "Book not found")
    fmt = book.format.value if hasattr(book.format, 'value') else book.format
    return {"toc": get_book_toc(book.file_path, fmt)}


@router.get("/{book_id}/chapter/{chapter_index}")
async def get_chapter(book_id: int, chapter_index: int, db: AsyncSession = Depends(get_db)):
    book = (await db.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if not book:
        raise HTTPException(404, "Book not found")
    fmt = book.format.value if hasattr(book.format, 'value') else book.format

    if fmt == "epub":
        result = get_epub_chapter_html(book.file_path, chapter_index)
        if not result["html"]:
            raise HTTPException(404, f"Chapter {chapter_index} not found")
        return result

    content = get_chapter_content(book.file_path, fmt, chapter_index)
    return {"content": content, "chapter_index": chapter_index, "title": f"Chapter {chapter_index + 1}", "total": 1}


@router.get("/{book_id}/page/{page_num}")
async def get_page(book_id: int, page_num: int, db: AsyncSession = Depends(get_db)):
    book = (await db.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if not book:
        raise HTTPException(404, "Book not found")
    fmt = book.format.value if hasattr(book.format, 'value') else book.format
    if fmt != "pdf":
        raise HTTPException(400, "Page API is for PDF only")
    from ..services.reader_service import convert_pdf_page_to_image
    img_path = convert_pdf_page_to_image(book.file_path, book.id, page_num)
    return FileResponse(img_path, media_type="image/png")


@router.get("/cover/{cover_path:path}")
async def get_cover(cover_path: str):
    full_path = CACHE_DIR / cover_path
    if os.path.exists(full_path):
        return FileResponse(full_path)
    raise HTTPException(404)
