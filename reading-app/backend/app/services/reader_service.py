import os
import json
import uuid
from pathlib import Path
from ..core.config import CACHE_DIR


def convert_epub_to_html(file_path: str, book_id: int) -> dict:
    """Convert EPUB to a JSON structure of chapters with HTML content."""
    from ebooklib import epub
    from bs4 import BeautifulSoup
    book = epub.read_epub(file_path)
    chapters = []
    spine = []
    try:
        spine = [item for item in book.get_items_of_type(9)]
    except Exception:
        pass
    if not spine:
        for item in book.get_items():
            if item.get_type() == 9:
                spine.append(item)

    css_content = ""
    for item in book.get_items_of_type(5):
        css_content += item.get_content().decode("utf-8", errors="ignore") + "\n"

    images_map = {}
    for item in book.get_items():
        if item.get_type() == 7:
            ext = Path(item.get_name()).suffix.lower()
            img_name = f"{uuid.uuid4().hex}{ext}"
            img_path = CACHE_DIR / "images" / img_name
            img_path.parent.mkdir(parents=True, exist_ok=True)
            img_path.write_bytes(item.get_content())
            images_map[item.get_name()] = f"/static/cache/images/{img_name}"

    for i, item in enumerate(spine):
        try:
            html = item.get_body_content().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            # Fix image paths
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if src in images_map:
                    img["src"] = images_map[src]
            title = ""
            for h in soup.find_all(["h1", "h2", "h3"]):
                title = h.get_text().strip()
                break
            chapters.append({
                "index": i,
                "title": title or f"Chapter {i+1}",
                "content": str(soup),
            })
        except Exception:
            chapters.append({"index": i, "title": f"Chapter {i+1}", "content": ""})
    return {"chapters": chapters, "css": css_content, "format": "epub"}


def convert_pdf_to_html(file_path: str, book_id: int) -> dict:
    """Return PDF metadata; actual rendering is done client-side with PDF.js."""
    import fitz
    doc = fitz.open(file_path)
    pages = []
    for i in range(doc.page_count):
        page = doc[i]
        pages.append({
            "index": i,
            "text": page.get_text(),
            "width": page.rect.width,
            "height": page.rect.height,
        })
    doc.close()
    return {"pages": pages, "total_pages": len(pages), "format": "pdf"}


def convert_pdf_page_to_image(file_path: str, book_id: int, page_num: int) -> str:
    """Render a PDF page as PNG image."""
    import fitz
    cache_key = f"pdf_{book_id}_p{page_num}.png"
    cache_path = CACHE_DIR / "pdf_pages" / cache_key
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        return str(cache_path)
    doc = fitz.open(file_path)
    page = doc[page_num]
    pix = page.get_pixmap(dpi=150)
    pix.save(str(cache_path))
    doc.close()
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

    # Fallback: try to extract text from the raw file
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        # Try to decode as UTF-8 and extract readable paragraphs
        text = data.decode("utf-8", errors="ignore")
        import re
        # Keep only paragraphs with meaningful content (Chinese + ASCII)
        paragraphs = re.findall(r'[一-鿿　-〿＀-￯\x20-\x7e]{20,}', text)
        if paragraphs:
            return "\n\n".join(paragraphs)
    except Exception:
        pass

    return "MOBI format: Full text extraction requires the 'mobi' Python package. Install with: pip install mobi"



def get_book_toc(file_path: str, fmt: str) -> list[dict]:
    try:
        if fmt == "epub":
            from ebooklib import epub
            book = epub.read_epub(file_path)
            toc = []
            for item in book.toc:
                if isinstance(item, tuple) and len(item) >= 2:
                    toc.append({"title": str(item[0]), "href": str(item[1])})
                elif hasattr(item, "title"):
                    toc.append({"title": item.title, "href": getattr(item, "href", "")})
            return toc
        elif fmt == "pdf":
            import fitz
            doc = fitz.open(file_path)
            toc = doc.get_toc()
            doc.close()
            return [{"level": t[0], "title": t[1], "page": t[2] - 1} for t in toc]
    except Exception:
        pass
    return []


def get_chapter_content(file_path: str, fmt: str, chapter_index: int) -> str:
    if fmt == "epub":
        from ebooklib import epub
        from bs4 import BeautifulSoup
        book = epub.read_epub(file_path)
        items = list(book.get_items_of_type(9))
        if chapter_index < len(items):
            return BeautifulSoup(
                items[chapter_index].get_body_content().decode("utf-8", errors="ignore"),
                "html.parser"
            ).get_text()
    elif fmt == "pdf":
        import fitz
        doc = fitz.open(file_path)
        if chapter_index < doc.page_count:
            return doc[chapter_index].get_text()
        doc.close()
    return ""
