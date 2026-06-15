#!/usr/bin/env python3
r"""Build a local book index from D:\onlinereading for Knowledge OS."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOK_ROOT = Path(r"D:\onlinereading")
OUTPUT = ROOT / "web" / "data" / "book-index.json"
SUPPORTED_EXTENSIONS = {".pdf", ".epub", ".mobi", ".azw3", ".txt"}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "哲学": [
        "哲学", "孔子", "孟子", "老子", "庄子", "王阳明", "苏格拉底", "柏拉图", "亚里士多德",
        "笛卡尔", "休谟", "康德", "黑格尔", "尼采", "马克思", "海德格尔", "维特根斯坦",
        "福柯", "弗洛伊德", "荣格", "存在", "伦理", "理性批判", "查拉图斯特拉", "纯粹理性",
    ],
    "心理学": [
        "心理", "认知", "行为", "情绪", "人格", "自卑", "亲密关系", "乌合之众", "阿德勒",
        "弗洛伊德", "荣格", "动机", "决策", "习惯", "学习",
    ],
    "脑科学": ["脑", "神经", "多巴胺", "睡眠", "意识", "记忆", "杏仁核", "海马体", "前额叶"],
    "佛学": ["佛", "禅", "心经", "金刚经", "修行", "正念", "觉察", "般若", "无常"],
    "美学": ["美学", "艺术", "设计", "审美", "风格", "视觉", "建筑", "摄影", "色彩"],
    "品牌传播": ["品牌", "营销", "传播", "广告", "流量", "成交", "定位", "叙事", "符号"],
    "经济金融": [
        "经济", "金融", "投资", "交易", "股票", "期货", "资本", "货币", "估值", "穷查理",
        "证券", "基金", "巴菲特", "芒格", "索罗斯",
    ],
    "商业产业": ["商业", "战略", "管理", "供应链", "产业", "组织", "创新", "公司", "增长"],
    "科技AI": [
        "人工智能", "AI", "机器学习", "深度学习", "Python", "算法", "数据", "科技", "芯片",
        "机器人", "互联网", "计算机",
    ],
    "历史文明": ["历史", "文明", "史记", "晚清", "中国史", "世界史", "人类简史", "全球通史"],
    "医学健康": ["医学", "健康", "营养", "疾病", "医生", "生命", "基因", "免疫", "癌症"],
    "文学": ["小说", "文学", "诗", "三体", "鲁迅", "村上", "故事", "散文"],
}


def main() -> int:
    if not BOOK_ROOT.exists():
        raise SystemExit(f"book root not found: {BOOK_ROOT}")

    books = []
    for path in sorted(BOOK_ROOT.rglob("*")):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        rel = path.relative_to(BOOK_ROOT).as_posix()
        title = clean_title(path.stem)
        text = f"{title} {rel} {' '.join(path.parts)}"
        books.append(
            {
                "id": make_id(rel),
                "title": title,
                "path": str(path),
                "relative_path": rel,
                "folder": path.parent.name,
                "extension": ext,
                "size": path.stat().st_size,
                "size_label": size_label(path.stat().st_size),
                "categories": classify(text),
                "search_text": normalize_text(text),
            }
        )

    data = {
        "generated_at": "local",
        "root": str(BOOK_ROOT),
        "count": len(books),
        "books": books,
        "categories": count_categories(books),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(books)} books)")
    return 0


def make_id(relative_path: str) -> str:
    return hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:16]


def clean_title(value: str) -> str:
    value = re.sub(r"【[^】]*】", "", value)
    value = re.sub(r"\[[^\]]*\]", "", value)
    value = re.sub(r"\([^)]*(公众号|Z-Library|微信|mobi|epub|pdf)[^)]*\)", "", value, flags=re.I)
    value = re.sub(r"^\d+[\s._-]*", "", value)
    value = re.sub(r"\s+", " ", value).strip(" ._-")
    return value or "未命名书籍"


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).lower()


def classify(text: str) -> list[str]:
    lowered = normalize_text(text)
    result = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            result.append(category)
    return result or ["未分类"]


def count_categories(books: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for book in books:
        for category in book["categories"]:
            counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def size_label(size: int) -> str:
    if size >= 1024 * 1024 * 1024:
        return f"{size / 1024 / 1024 / 1024:.1f} GB"
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


if __name__ == "__main__":
    raise SystemExit(main())
