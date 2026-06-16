import html
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests
from dotenv import load_dotenv

from zen_trader.exceptions import ZenTraderError


class WeChatPublishError(ZenTraderError):
    """Raised when WeChat official account publishing fails."""


@dataclass
class WeChatArticle:
    title: str
    body: str
    digest: str = ""
    author: str = ""
    content_source_url: str = ""


class WeChatOfficialPublisher:
    token_url = "https://api.weixin.qq.com/cgi-bin/token"
    material_url = "https://api.weixin.qq.com/cgi-bin/material/add_material"
    draft_url = "https://api.weixin.qq.com/cgi-bin/draft/add"

    def __init__(self):
        load_dotenv()
        self.app_id = os.getenv("WECHAT_APP_ID", "").strip()
        self.app_secret = os.getenv("WECHAT_APP_SECRET", "").strip()
        self.author = os.getenv("WECHAT_AUTHOR", "").strip()
        self.digest = os.getenv("WECHAT_DIGEST", "禅意复盘").strip() or "禅意复盘"
        self.default_thumb_media_id = os.getenv("WECHAT_THUMB_MEDIA_ID", "").strip()
        self.timeout = float(os.getenv("WECHAT_TIMEOUT", "30"))
        if not self.app_id or not self.app_secret:
            raise WeChatPublishError("缺少 WECHAT_APP_ID 或 WECHAT_APP_SECRET")

    def save_draft(self, article: WeChatArticle) -> dict:
        article = self._normalize_article(article)
        token = self._access_token()
        thumb_media_id = self.default_thumb_media_id or self._upload_default_cover(token, article.title)
        payload = {
            "articles": [
                {
                    "title": self._clip_utf8(article.title, 96) or "禅意复盘",
                    "author": self._clip_utf8(article.author or self.author, 24),
                    "digest": self._clip_utf8(article.digest or self.digest, 36),
                    "content": self._to_wechat_html(article),
                    "content_source_url": article.content_source_url,
                    "thumb_media_id": thumb_media_id,
                    "need_open_comment": 0,
                    "only_fans_can_comment": 0,
                }
            ]
        }
        data = self._post_json(self.draft_url, token, payload)
        return {"media_id": data.get("media_id"), "thumb_media_id": thumb_media_id, "raw": data}

    def _access_token(self) -> str:
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
        }
        try:
            resp = requests.get(self.token_url, params=params, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise WeChatPublishError(f"获取 access_token 失败: {e}") from e
        data = resp.json()
        self._raise_for_wechat_error(data, "获取 access_token 失败")
        token = data.get("access_token")
        if not token:
            raise WeChatPublishError(f"获取 access_token 失败: {data}")
        return token

    def _upload_default_cover(self, token: str, title: str) -> str:
        cover_path = self._make_cover(title)
        params = {"access_token": token, "type": "image"}
        try:
            with open(cover_path, "rb") as fh:
                files = {"media": (cover_path.name, fh, "image/png")}
                resp = requests.post(self.material_url, params=params, files=files, timeout=self.timeout)
                resp.raise_for_status()
        except requests.RequestException as e:
            raise WeChatPublishError(f"上传公众号封面失败: {e}") from e
        data = resp.json()
        self._raise_for_wechat_error(data, "上传公众号封面失败")
        media_id = data.get("media_id")
        if not media_id:
            raise WeChatPublishError(f"上传公众号封面失败: {data}")
        return media_id

    def _make_cover(self, title: str) -> Path:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError as e:
            raise WeChatPublishError("缺少 Pillow，无法生成默认封面图") from e

        width, height = 900, 383
        img = Image.new("RGB", (width, height), "#111827")
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, width, height), fill="#111827")
        draw.rectangle((34, 34, width - 34, height - 34), outline="#d4a574", width=4)
        draw.text((70, 78), "悟道之行2022", fill="#d4a574", font=self._font(34))
        title_font = self._font(46)
        lines = self._wrap_title(title or "禅意复盘", title_font, width - 110, 2)
        y = 165
        for line in lines:
            draw.text((70, y), line, fill="#f8fafc", font=title_font)
            y += 62
        path = Path(tempfile.gettempdir()) / "media_factory_wechat_cover.png"
        img.save(path, format="PNG", optimize=True)
        return path

    @staticmethod
    def _font(size: int):
        from PIL import ImageFont

        candidates = [os.getenv("WECHAT_COVER_FONT", "").strip()]
        candidates.extend(
            WeChatOfficialPublisher._fontconfig_candidates(
                [
                    "Noto Sans CJK SC",
                    "Noto Sans CJK",
                    "WenQuanYi Micro Hei",
                    "WenQuanYi Zen Hei",
                    "Microsoft YaHei",
                    "SimHei",
                ]
            )
        )
        candidates.extend(
            [
                "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/google-noto-cjk/NotoSansCJKsc-Regular.otf",
                "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
                "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/msyh.ttf",
                "C:/Windows/Fonts/simsun.ttc",
                "C:/Windows/Fonts/simhei.ttf",
            ]
        )
        seen = set()
        for path in candidates:
            if not path or path in seen:
                continue
            seen.add(path)
            if Path(path).exists():
                try:
                    return ImageFont.truetype(path, size)
                except OSError:
                    continue
        return ImageFont.load_default()

    @staticmethod
    def _fontconfig_candidates(families: list[str]) -> list[str]:
        paths = []
        for family in families:
            try:
                result = subprocess.run(
                    ["fc-match", "-f", "%{file}", family],
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=2,
                )
            except (OSError, subprocess.SubprocessError):
                continue
            path = result.stdout.strip()
            if path:
                paths.append(path)
        return paths

    @staticmethod
    def _wrap_title(title: str, font, max_width: int, max_lines: int) -> list[str]:
        clean = re.sub(r"\s+", " ", title).strip()
        if not clean:
            return ["禅意复盘"]
        lines = []
        index = 0
        while index < len(clean) and len(lines) < max_lines:
            current = ""
            while index < len(clean):
                candidate = current + clean[index]
                if not current or WeChatOfficialPublisher._text_width(candidate, font) <= max_width:
                    current = candidate
                    index += 1
                else:
                    break
            lines.append(current)
        if index < len(clean) and lines:
            ellipsis = "…"
            last = lines[-1].rstrip()
            while last and WeChatOfficialPublisher._text_width(last + ellipsis, font) > max_width:
                last = last[:-1].rstrip()
            lines[-1] = (last or lines[-1][:1]) + ellipsis
        return lines

    @staticmethod
    def _text_width(text: str, font) -> float:
        if hasattr(font, "getlength"):
            return font.getlength(text)
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]

    def _to_wechat_html(self, article: WeChatArticle) -> str:
        body = self._strip_duplicate_title(article.title, article.body)
        parts = [
            '<section style="max-width:100%;box-sizing:border-box;padding:0 2px;color:#1f2937;font-size:16px;line-height:1.95;letter-spacing:0;">',
            '<section style="margin:0 0 26px;padding:26px 22px 24px;border-radius:0;background:#111827;color:#f9fafb;">',
            '<p style="margin:0 0 12px;color:#d4a574;font-size:13px;letter-spacing:0;">悟道之行2022 · 禅意复盘</p>',
            f'<h1 style="margin:0;color:#fff;font-size:24px;line-height:1.42;font-weight:700;">{html.escape(article.title)}</h1>',
            f'<p style="margin:18px 0 0;color:#d1d5db;font-size:14px;line-height:1.8;">{html.escape(self._clip_utf8(self._digest(article.body), 180))}</p>',
            '</section>',
        ]
        for block in self._blocks(body):
            if block.startswith("#"):
                text = block.lstrip("#").strip()
                parts.append(
                    '<section style="margin:30px 0 14px;padding:0 0 0 12px;border-left:4px solid #d4a574;">'
                    f'<h2 style="margin:0;color:#8a5a2b;font-size:19px;line-height:1.5;font-weight:700;">{html.escape(text)}</h2>'
                    '</section>'
                )
            elif block.startswith(("- ", "* ", "• ")):
                items = [html.escape(line.lstrip("-*• ").strip()) for line in block.splitlines()]
                parts.append('<section style="margin:12px 0 20px;padding:14px 16px;background:#f9fafb;border:1px solid #edf0f3;border-radius:0;">')
                parts.append('<ul style="margin:0;padding-left:1.15em;color:#374151;">')
                parts.extend(f'<li style="margin:6px 0;">{item}</li>' for item in items if item)
                parts.append("</ul>")
                parts.append("</section>")
            elif block.strip() == "---":
                parts.append('<section style="margin:28px auto;width:52px;border-top:2px solid #d4a574;"></section>')
            else:
                text = html.escape(block).replace("\n", "<br />")
                parts.append(
                    f'<p style="margin:0 0 17px;color:#1f2937;font-size:16px;line-height:1.95;">{text}</p>'
                )
        parts.append(
            '<section style="margin:34px 0 0;padding:18px 18px;background:#faf7f1;border-left:4px solid #d4a574;">'
            '<p style="margin:0;color:#6b7280;font-size:14px;line-height:1.8;">'
            '市场有涨跌，人心有起伏。复盘不是为了预测一切，而是为了在不确定里保持清明。'
            '</p>'
            '</section>'
        )
        parts.append("</section>")
        return "".join(parts)

    @staticmethod
    def _strip_duplicate_title(title: str, body: str) -> str:
        lines = body.strip().splitlines()
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines:
            first = lines[0].strip().lstrip("#").strip()
            if first == title.strip():
                lines.pop(0)
        return "\n".join(lines).strip()

    @staticmethod
    def _blocks(text: str) -> list[str]:
        blocks = []
        current = []
        for line in text.splitlines():
            if line.strip():
                current.append(line.rstrip())
            elif current:
                blocks.append("\n".join(current).strip())
                current = []
        if current:
            blocks.append("\n".join(current).strip())
        return blocks

    @staticmethod
    def _digest(body: str) -> str:
        text = re.sub(r"[#>*_`\\-]+", "", body)
        text = re.sub(r"\s+", " ", text).strip()
        return text or "禅意复盘"

    @staticmethod
    def _clip_utf8(text: str, max_bytes: int) -> str:
        text = (text or "").strip()
        if len(text.encode("utf-8")) <= max_bytes:
            return text
        suffix = "…" if max_bytes >= 6 else ""
        limit = max_bytes - len(suffix.encode("utf-8"))
        clipped = text.encode("utf-8")[:limit]
        return clipped.decode("utf-8", "ignore").rstrip("，。；、,. ;:：") + suffix

    @staticmethod
    def _raise_for_wechat_error(data: dict, prefix: str) -> None:
        errcode = data.get("errcode", 0)
        if errcode not in (0, "0", None):
            errmsg = data.get("errmsg", data)
            raise WeChatPublishError(f"{prefix}: errcode={errcode}, errmsg={errmsg}")

    def _post_json(self, url: str, token: str, payload: dict) -> dict:
        try:
            resp = requests.post(
                url,
                params={"access_token": token},
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise WeChatPublishError(f"请求微信公众号接口失败: {e}") from e
        data = resp.json()
        self._raise_for_wechat_error(data, "微信公众号接口返回错误")
        return data

    @classmethod
    def _normalize_article(cls, article: WeChatArticle) -> WeChatArticle:
        return WeChatArticle(
            title=cls._decode_unicode_escapes(article.title),
            body=cls._decode_unicode_escapes(article.body),
            digest=cls._decode_unicode_escapes(article.digest),
            author=cls._decode_unicode_escapes(article.author),
            content_source_url=article.content_source_url,
        )

    @staticmethod
    def _decode_unicode_escapes(text: str) -> str:
        text = text or ""
        if "\\u" not in text and "\\U" not in text:
            return text
        def surrogate_repl(match):
            high = int(match.group(1), 16)
            low = int(match.group(2), 16)
            codepoint = 0x10000 + ((high - 0xD800) << 10) + (low - 0xDC00)
            return chr(codepoint)

        def repl(match):
            try:
                code = int(match.group(1), 16)
                if 0xD800 <= code <= 0xDFFF:
                    return match.group(0)
                return chr(code)
            except ValueError:
                return match.group(0)

        text = re.sub(r"\\u(d[89abAB][0-9a-fA-F]{2})\\u(d[cdefCDEF][0-9a-fA-F]{2})", surrogate_repl, text)
        return re.sub(r"\\u([0-9a-fA-F]{4})", repl, text)
