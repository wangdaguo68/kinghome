import os
import time
from pathlib import Path
from ..core.config import CACHE_DIR

# ---------- TTL cache for opened documents ----------
_ttl_cache: dict = {}
_CACHE_TTL = 300  # 5 minutes
_CACHE_MAX = 16

def _cache_get(key: str):
    entry = _ttl_cache.get(key)
    if entry and time.time() - entry[0] < _CACHE_TTL:
        _ttl_cache[key] = (time.time(), entry[1])  # bump
        return entry[1]
    return None

def _cache_set(key: str, value):
    if len(_ttl_cache) >= _CACHE_MAX:
        oldest = min(_ttl_cache, key=lambda k: _ttl_cache[k][0])
        del _ttl_cache[oldest]
    _ttl_cache[key] = (time.time(), value)


def _get_cached_pdf_doc(file_path: str):
    """Return a fitz.Document, cached in memory for 5 min."""
    key = f"pdf_doc:{file_path}"
    doc = _cache_get(key)
    if doc is not None:
        return doc
    import fitz
    doc = fitz.open(file_path)
    _cache_set(key, doc)
    return doc


def _get_cached_epub_book(file_path: str):
    """Return a parsed epub book object, cached in memory for 5 min."""
    key = f"epub_book:{file_path}"
    book = _cache_get(key)
    if book is not None:
        return book
    from ebooklib import epub
    book = epub.read_epub(file_path)
    _cache_set(key, book)
    return book


def _cached_epub_images(file_path: str) -> dict[str, str]:
    """Extract images from EPUB, cached. Returns {orig_name: cache_url}."""
    key = f"epub_images:{file_path}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    book = _get_cached_epub_book(file_path)
    images_map = {}
    for item in book.get_items():
        if item.get_type() == 7:  # ITEM_IMAGE
            safe_name = item.get_name().replace("/", "_").replace("\\", "_")
            img_path = CACHE_DIR / "images" / safe_name
            img_path.parent.mkdir(parents=True, exist_ok=True)
            if not img_path.exists():
                img_path.write_bytes(item.get_content())
            images_map[item.get_name()] = f"/static/cache/images/{safe_name}"
    _cache_set(key, images_map)
    return images_map


def _cached_epub_css(file_path: str) -> str:
    """Extract CSS from EPUB, cached."""
    key = f"epub_css:{file_path}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    book = _get_cached_epub_book(file_path)
    css_parts = []
    for item in book.get_items_of_type(5):  # ITEM_STYLE
        css_parts.append(item.get_content().decode("utf-8", errors="ignore"))
    css = "\n".join(css_parts)
    _cache_set(key, css)
    return css


def get_epub_chapter_html(file_path: str, chapter_index: int) -> dict:
    """Return a single EPUB chapter as HTML with CSS and resolved image paths."""
    from bs4 import BeautifulSoup

    book = _get_cached_epub_book(file_path)
    spine = list(book.get_items_of_type(9))  # ITEM_DOCUMENT
    if not spine:
        for item in book.get_items():
            if item.get_type() == 9:
                spine.append(item)

    if chapter_index < 0 or chapter_index >= len(spine):
        return {"html": "", "title": "", "css": "", "index": chapter_index, "total": len(spine)}

    images_map = _cached_epub_images(file_path)
    css = _cached_epub_css(file_path)

    item = spine[chapter_index]
    html = item.get_body_content().decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    # Fix image paths
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src in images_map:
            img["src"] = images_map[src]
        elif src:
            for orig, cache_url in images_map.items():
                if orig.endswith(src) or src.endswith(orig):
                    img["src"] = cache_url
                    break

    title = f"Chapter {chapter_index + 1}"
    for h in soup.find_all(["h1", "h2", "h3"]):
        t = h.get_text().strip()
        if t:
            title = t
            break

    return {
        "html": str(soup),
        "title": title,
        "css": css,
        "index": chapter_index,
        "total": len(spine),
    }


def convert_epub_to_html(file_path: str, book_id: int) -> dict:
    """Convert EPUB to a JSON structure of chapters with HTML content."""
    book = _get_cached_epub_book(file_path)
    spine = list(book.get_items_of_type(9))
    if not spine:
        for item in book.get_items():
            if item.get_type() == 9:
                spine.append(item)
    total = len(spine)
    chapters_meta = []
    for i in range(total):
        title = f"Chapter {i + 1}"
        try:
            from bs4 import BeautifulSoup
            html = spine[i].get_body_content().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            for h in soup.find_all(["h1", "h2", "h3"]):
                title = h.get_text().strip()
                break
        except Exception:
            pass
        chapters_meta.append({"index": i, "title": title})
    return {"chapters": chapters_meta, "total_chapters": total, "format": "epub"}


def convert_pdf_to_html(file_path: str, book_id: int) -> dict:
    """Return PDF page count only — page images are served separately."""
    doc = _get_cached_pdf_doc(file_path)
    total = doc.page_count
    return {"total_pages": total, "format": "pdf"}


def convert_pdf_page_to_image(file_path: str, book_id: int, page_num: int) -> str:
    """Render a PDF page as PNG image (cached on disk)."""
    import fitz
    cache_key = f"pdf_{book_id}_p{page_num}.png"
    cache_path = CACHE_DIR / "pdf_pages" / cache_key
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        return str(cache_path)
    doc = _get_cached_pdf_doc(file_path)
    page = doc[page_num]
    pix = page.get_pixmap(dpi=150)
    pix.save(str(cache_path))
    return str(cache_path)


def convert_mobi_to_text(file_path: str) -> str:
    """Extract readable text from MOBI file."""
    try:
        from mobi import Mobi
        book = Mobi(file_path)
        book.parse()
        text = ""
        for record in book:
            if hasattr(record, 'text') and record.text:
                text += record.text + "\n\n"
        if text.strip():
            return text
    except ImportError:
        pass
    except Exception:
        pass

    try:
        with open(file_path, "rb") as f:
            data = f.read()
        text = data.decode("utf-8", errors="ignore")
        import re
        paragraphs = re.findall(r'[一-鿿　-〿＀-￯\x20-\x7e]{20,}', text)
        if paragraphs:
            return "\n\n".join(paragraphs)
    except Exception:
        pass

    return "MOBI format: Full text extraction requires the 'mobi' Python package. Install with: pip install mobi"


def get_book_toc(file_path: str, fmt: str) -> list[dict]:
    try:
        if fmt == "epub":
            book = _get_cached_epub_book(file_path)
            toc = []
            for item in book.toc:
                if isinstance(item, tuple) and len(item) >= 2:
                    toc.append({"title": str(item[0]), "href": str(item[1])})
                elif hasattr(item, "title"):
                    toc.append({"title": item.title, "href": getattr(item, "href", "")})
            return toc
        elif fmt == "pdf":
            doc = _get_cached_pdf_doc(file_path)
            toc = doc.get_toc()
            return [{"level": t[0], "title": t[1], "page": t[2] - 1} for t in toc]
    except Exception:
        pass
    return []


def get_chapter_content(file_path: str, fmt: str, chapter_index: int) -> str:
    if fmt == "epub":
        from bs4 import BeautifulSoup
        book = _get_cached_epub_book(file_path)
        items = list(book.get_items_of_type(9))
        if chapter_index < len(items):
            return BeautifulSoup(
                items[chapter_index].get_body_content().decode("utf-8", errors="ignore"),
                "html.parser"
            ).get_text()
    elif fmt == "pdf":
        doc = _get_cached_pdf_doc(file_path)
        if chapter_index < doc.page_count:
            return doc[chapter_index].get_text()
    return ""
