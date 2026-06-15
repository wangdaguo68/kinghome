#!/usr/bin/env python3
"""Serve Knowledge OS and local books from one localhost origin."""

from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
import re
import urllib.parse
import zipfile
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"
BOOK_INDEX = WEB_ROOT / "data" / "book-index.json"


class KnowledgeHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/books/read/"):
            self.handle_book_read(parsed.path.rsplit("/", 1)[-1])
            return
        if parsed.path.startswith("/books/file/"):
            self.handle_book_file(parsed.path.rsplit("/", 1)[-1])
            return
        if parsed.path.startswith("/books/open/"):
            self.handle_book_open(parsed.path.rsplit("/", 1)[-1])
            return
        super().do_GET()

    def handle_book_read(self, book_id: str) -> None:
        book = self.find_book(book_id)
        if not book:
            self.send_text("Book not found", HTTPStatus.NOT_FOUND)
            return

        path = Path(book["path"])
        ext = path.suffix.lower()
        if ext == ".pdf":
            body = f"""
            <main class="reader-page">
              <header><h1>{html.escape(book["title"])}</h1><p>{html.escape(book["relative_path"])}</p></header>
              <iframe src="/books/file/{book_id}" title="{html.escape(book["title"])}"></iframe>
            </main>
            """
            self.send_html(self.page_shell(book["title"], body, extra_css="iframe{width:100%;height:calc(100vh - 110px);border:0}"))
            return
        if ext == ".txt":
            text = path.read_text(encoding="utf-8", errors="ignore")
            body = f"<article class=\"text-reader\"><h1>{html.escape(book['title'])}</h1><pre>{html.escape(text)}</pre></article>"
            self.send_html(self.page_shell(book["title"], body, extra_css="pre{white-space:pre-wrap;line-height:1.8}"))
            return
        if ext == ".epub":
            body = self.render_epub(book)
            self.send_html(self.page_shell(book["title"], body))
            return

        body = f"""
        <main class="reader-page">
          <header><h1>{html.escape(book["title"])}</h1><p>{html.escape(book["relative_path"])}</p></header>
          <section class="fallback">
            <p>这种格式（{html.escape(ext)}）浏览器不能直接稳定解析。你可以用本机默认阅读器打开，或下载/打开原文件。</p>
            <p><a href="/books/open/{book_id}">用本机阅读器打开</a> <a href="/books/file/{book_id}">下载/打开原文件</a></p>
          </section>
        </main>
        """
        self.send_html(self.page_shell(book["title"], body))

    def render_epub(self, book: dict) -> str:
        path = Path(book["path"])
        try:
            with zipfile.ZipFile(path) as archive:
                container = ET.fromstring(archive.read("META-INF/container.xml"))
                ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
                rootfile = container.find(".//c:rootfile", ns)
                if rootfile is None:
                    raise ValueError("missing rootfile")
                opf_path = rootfile.attrib["full-path"]
                opf_dir = str(Path(opf_path).parent).replace("\\", "/")
                if opf_dir == ".":
                    opf_dir = ""
                opf = ET.fromstring(archive.read(opf_path))
                manifest = {}
                for item in opf.findall(".//{*}manifest/{*}item"):
                    manifest[item.attrib.get("id", "")] = item.attrib.get("href", "")
                html_parts = []
                for itemref in opf.findall(".//{*}spine/{*}itemref"):
                    href = manifest.get(itemref.attrib.get("idref", ""))
                    if not href:
                        continue
                    chapter_path = f"{opf_dir}/{href}" if opf_dir else href
                    chapter_path = urllib.parse.unquote(chapter_path)
                    if chapter_path not in archive.namelist():
                        continue
                    raw = archive.read(chapter_path).decode("utf-8", errors="ignore")
                    body = extract_body(raw)
                    if body:
                        html_parts.append(body)
                content = "\n".join(html_parts) or "<p>未能解析 EPUB 正文。</p>"
        except Exception as error:
            content = (
                f"<p>EPUB 解析失败：{html.escape(str(error))}</p>"
                f"<p><a href=\"/books/open/{book['id']}\">用本机阅读器打开</a></p>"
            )

        return f"""
        <article class="epub-reader">
          <header><h1>{html.escape(book["title"])}</h1><p>{html.escape(book["relative_path"])}</p></header>
          {content}
        </article>
        """

    def handle_book_file(self, book_id: str) -> None:
        book = self.find_book(book_id)
        if not book:
            self.send_text("Book not found", HTTPStatus.NOT_FOUND)
            return
        path = Path(book["path"])
        if not path.exists():
            self.send_text("File not found", HTTPStatus.NOT_FOUND)
            return
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("Content-Disposition", f"inline; filename*=UTF-8''{urllib.parse.quote(path.name)}")
        self.end_headers()
        with path.open("rb") as source:
            while chunk := source.read(1024 * 512):
                self.wfile.write(chunk)

    def handle_book_open(self, book_id: str) -> None:
        book = self.find_book(book_id)
        if not book:
            self.send_text("Book not found", HTTPStatus.NOT_FOUND)
            return
        path = Path(book["path"])
        if path.exists():
            os.startfile(str(path))  # type: ignore[attr-defined]
        body = f"<main class=\"reader-page\"><h1>已尝试打开：{html.escape(book['title'])}</h1><p>{html.escape(str(path))}</p></main>"
        self.send_html(self.page_shell("打开本地书籍", body))

    def find_book(self, book_id: str) -> dict | None:
        if not BOOK_INDEX.exists():
            return None
        data = json.loads(BOOK_INDEX.read_text(encoding="utf-8"))
        return next((book for book in data.get("books", []) if book.get("id") == book_id), None)

    def send_text(self, text: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_html(self, text: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def page_shell(self, title: str, body: str, extra_css: str = "") -> str:
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body{{margin:0;background:#f6f2ea;color:#20231f;font-family:"Microsoft YaHei UI","Segoe UI",sans-serif}}
    a{{color:#0d6658;font-weight:800}}
    .reader-page,.epub-reader,.text-reader{{max-width:980px;margin:0 auto;padding:24px;background:#fffdf7;min-height:100vh}}
    header{{border-bottom:1px solid #d9d0c2;margin-bottom:18px;padding-bottom:12px}}
    h1{{font-size:26px;margin:0 0 8px}}
    h2{{border-top:1px solid #d9d0c2;padding-top:18px;margin-top:24px}}
    p,li{{line-height:1.85}}
    img{{max-width:100%}}
    .fallback{{border:1px solid #d9d0c2;background:#fff;padding:16px}}
    {extra_css}
  </style>
</head>
<body>{body}</body>
</html>"""


def extract_body(raw: str) -> str:
    raw = re.sub(r"<script[\s\S]*?</script>", "", raw, flags=re.I)
    raw = re.sub(r"<style[\s\S]*?</style>", "", raw, flags=re.I)
    match = re.search(r"<body[^>]*>([\s\S]*?)</body>", raw, flags=re.I)
    body = match.group(1) if match else raw
    body = re.sub(r"\s(on\w+)=['\"][^'\"]*['\"]", "", body, flags=re.I)
    return body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8793)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), KnowledgeHandler)
    print(f"Knowledge OS server: http://127.0.0.1:{args.port}/index.html")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
