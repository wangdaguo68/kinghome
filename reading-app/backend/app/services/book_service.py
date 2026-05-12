import os
import logging
import uuid
from pathlib import Path
from ..core.config import BOOK_LIBRARY_DIR, CACHE_DIR

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".epub", ".mobi"}
FORMAT_MAP = {".pdf": "pdf", ".epub": "epub", ".mobi": "mobi"}


def scan_library() -> list[dict]:
    """Scan the book library directory and return file info for all supported books."""
    books = []
    for root, dirs, files in os.walk(BOOK_LIBRARY_DIR):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                full_path = Path(root) / f
                try:
                    st = full_path.stat()
                except OSError:
                    continue
                books.append({
                    "file_path": str(full_path),
                    "file_name": f,
                    "format": FORMAT_MAP[ext],
                    "file_size": st.st_size,
                    "folder": str(Path(root).relative_to(BOOK_LIBRARY_DIR)),
                })
    return books


def extract_metadata_from_pdf(file_path: str) -> dict:
    import fitz
    try:
        doc = fitz.open(file_path)
        try:
            meta = doc.metadata
            title = meta.get("title") or Path(file_path).stem
            author = meta.get("author") or ""
            page_count = doc.page_count
            desc = meta.get("subject") or ""
        finally:
            doc.close()
        return {"title": title, "author": author, "page_count": page_count,
                "description": desc, "publisher": ""}
    except Exception as e:
        logger.warning(f"PDF metadata extraction failed for {file_path}: {e}")
        raise


def extract_metadata_from_epub(file_path: str) -> dict:
    from ebooklib import epub
    book = epub.read_epub(file_path)
    title = ""
    author = ""
    publisher = ""
    desc = ""
    for item in book.get_metadata("DC", "title"):
        title = item[0]
        break
    for item in book.get_metadata("DC", "creator"):
        author = item[0]
        break
    for item in book.get_metadata("DC", "publisher"):
        publisher = item[0]
        break
    for item in book.get_metadata("DC", "description"):
        desc = item[0]
        break
    if not title:
        title = Path(file_path).stem
    page_count = len(list(book.get_items_of_type(9)))
    if page_count == 0:
        page_count = len([i for i in book.get_items() if i.get_type() == 9])
    return {"title": title, "author": author, "page_count": max(page_count, 1),
            "description": desc, "publisher": publisher,
            "cover_path": _extract_epub_cover(book, file_path)}


def _extract_epub_cover(book, file_path: str) -> str:
    from ebooklib import ITEM_IMAGE
    cover_id = None
    for _key, val in book.get_metadata("OPF", "meta"):
        if val.get("name") == "cover":
            cover_id = val.get("content")
            break
    cover_path = ""
    cover_filename = f"{uuid.uuid4().hex}.jpg"
    cover_dest = CACHE_DIR / "covers" / cover_filename
    cover_dest.parent.mkdir(parents=True, exist_ok=True)
    if cover_id:
        try:
            item = book.get_item_with_id(cover_id)
            if item:
                cover_dest.write_bytes(item.content)
                cover_path = f"/static/cache/covers/{cover_filename}"
                return cover_path
        except Exception as e:
            logger.debug(f"Cover extraction by ID failed: {e}")
    # Fallback: use first image
    for item in book.get_items_of_type(ITEM_IMAGE):
        try:
            cover_dest.write_bytes(item.content)
            cover_path = f"/static/cache/covers/{cover_filename}"
            break
        except Exception as e:
            logger.debug(f"Cover image write failed: {e}")
            continue
    return cover_path


def extract_metadata_from_mobi(file_path: str) -> dict:
    stem = Path(file_path).stem
    author = ""
    title = stem
    if " - " in stem:
        parts = stem.split(" - ", 1)
        author = parts[0].strip()
        title = parts[1].strip()
    return {"title": title, "author": author, "page_count": 0, "description": "", "publisher": ""}


def extract_metadata(file_path: str, fmt: str) -> dict:
    try:
        if fmt == "pdf":
            return extract_metadata_from_pdf(file_path)
        elif fmt == "epub":
            return extract_metadata_from_epub(file_path)
        elif fmt == "mobi":
            return extract_metadata_from_mobi(file_path)
    except Exception as e:
        logger.warning(f"Metadata extraction failed for {file_path}: {e}")
    stem = Path(file_path).stem
    return {"title": stem, "author": "", "page_count": 0, "description": "", "publisher": ""}


def extract_text_from_pdf(file_path: str) -> str:
    import fitz
    text_parts = []
    doc = fitz.open(file_path)
    try:
        for page in doc:
            text_parts.append(page.get_text())
    finally:
        doc.close()
    return "\n".join(text_parts)


def extract_text_from_epub(file_path: str) -> str:
    from ebooklib import epub
    from bs4 import BeautifulSoup
    book = epub.read_epub(file_path)
    texts = []
    for item in book.get_items_of_type(9):
        content = item.get_body_content()
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(content, "html.parser")
        texts.append(soup.get_text())
    return "\n".join(texts)


def extract_text_from_mobi(file_path: str) -> str:
    # MOBI text extraction is limited without calibre tools.
    # Return empty string; the book can still be read via epub.js conversion.
    logger.debug(f"MOBI text extraction skipped (not supported): {file_path}")
    return ""


def extract_text(file_path: str, fmt: str) -> str:
    try:
        if fmt == "pdf":
            return extract_text_from_pdf(file_path)
        elif fmt == "epub":
            return extract_text_from_epub(file_path)
        elif fmt == "mobi":
            return extract_text_from_mobi(file_path)
    except Exception as e:
        logger.warning(f"Text extraction failed for {file_path}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    import re
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) < chunk_size:
            current += para + "\n"
        else:
            if current:
                chunks.append(current.strip())
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[。！？.!?])', para)
                sub = ""
                for s in sentences:
                    if len(sub) + len(s) < chunk_size:
                        sub += s
                    else:
                        if sub:
                            chunks.append(sub.strip())
                        sub = s
                if sub:
                    current = sub + "\n"
                else:
                    current = ""
            else:
                current = para + "\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks
