import asyncio
import logging
import traceback
from pathlib import PurePath
from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from ..core.database import async_session
from ..models.book import Book
from ..services.book_service import scan_library, extract_metadata
from ..services.classification_service import classify_title
from ..schemas import ScanProgress

logger = logging.getLogger(__name__)
router = APIRouter()

_scan_lock = asyncio.Lock()
scan_state = {"total": 0, "processed": 0, "current_file": "", "is_complete": True, "error": ""}


@router.get("/status", response_model=ScanProgress)
async def scan_status():
    return ScanProgress(**scan_state)


@router.post("/start", response_model=ScanProgress)
async def start_scan():
    global scan_state
    if not scan_state["is_complete"]:
        return ScanProgress(**scan_state)

    async with _scan_lock:
        if not scan_state["is_complete"]:
            return ScanProgress(**scan_state)
        scan_state = {"total": 0, "processed": 0, "current_file": "", "is_complete": False, "error": ""}

    asyncio.create_task(_do_scan())
    return ScanProgress(**scan_state)


async def _do_scan():
    global scan_state
    try:
        # Run the blocking directory walk in a thread
        results = await asyncio.to_thread(scan_library)
        scan_state["total"] = len(results)
        logger.info(f"Scan found {len(results)} book files")

        for i, book_info in enumerate(results):
            scan_state["current_file"] = book_info["file_path"]
            scan_state["processed"] = i

            async with async_session() as db:
                try:
                    existing = (await db.execute(
                        select(Book).where(Book.file_path == book_info["file_path"])
                    )).scalar_one_or_none()
                    if existing:
                        continue

                    # Run blocking metadata extraction in a thread
                    meta = await asyncio.to_thread(
                        extract_metadata, book_info["file_path"], book_info["format"]
                    )

                    title = meta.get("title") or book_info["file_name"]
                    category, subcategory = classify_title(title)

                    book = Book(
                        title=title,
                        author=meta.get("author", ""),
                        publisher=meta.get("publisher", ""),
                        file_path=book_info["file_path"],
                        format=book_info["format"],
                        file_size=book_info["file_size"],
                        page_count=meta.get("page_count", 0),
                        description=meta.get("description", ""),
                        cover_path=meta.get("cover_path", ""),
                        category=category,
                        subcategory=subcategory,
                    )
                    db.add(book)
                    await db.commit()
                except IntegrityError:
                    await db.rollback()
                    logger.debug(f"Skipping duplicate: {book_info['file_path']}")
                except Exception as e:
                    await db.rollback()
                    logger.warning(f"Failed to import {book_info['file_path']}: {e}")

            # Yield control periodically to keep the event loop responsive
            if i % 10 == 0:
                await asyncio.sleep(0)

        scan_state["processed"] = scan_state["total"]
    except Exception as e:
        logger.error(f"Scan failed: {e}\n{traceback.format_exc()}")
        scan_state["error"] = str(e)
    finally:
        scan_state["is_complete"] = True
        scan_state["current_file"] = ""
