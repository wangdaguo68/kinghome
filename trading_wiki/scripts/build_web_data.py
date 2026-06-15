#!/usr/bin/env python3
"""Build a JSON index for the local Trading Wiki web app."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_FOLDERS = ["概念", "股票", "策略", "模式", "错误"]
AUDIT_FOLDERS = ["sources", "raw", "reports", "reviews"]
OUTPUT = ROOT / "web" / "data" / "wiki-index.json"
CONTENT_OUTPUT = ROOT / "web" / "content"
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
DEFAULT_DOMAINS = [
    "全部",
    "认知系统",
    "智能系统",
    "产业系统",
    "财富系统",
    "生命系统",
    "物理系统",
    "美学系统",
    "意义系统",
    "范式系统",
]


def main() -> int:
    pages = []
    for folder in KNOWLEDGE_FOLDERS + AUDIT_FOLDERS:
        for path in sorted((ROOT / folder).glob("*.md")):
            pages.append(parse_page(path))

    by_title = {page["title"]: page["id"] for page in pages}
    by_stem = {Path(page["path"]).stem: page["id"] for page in pages}

    edges = []
    for page in pages:
        resolved_links = []
        for target in page["wikilinks"]:
            target_id = by_title.get(target) or by_stem.get(target)
            if target_id and target_id != page["id"]:
                edge = {"source": page["id"], "target": target_id, "kind": "wikilink"}
                if edge not in edges:
                    edges.append(edge)
                resolved_links.append(target_id)
        page["resolved_links"] = resolved_links

    backlink_map = {page["id"]: [] for page in pages}
    for edge in edges:
        backlink_map[edge["target"]].append(edge["source"])
    for page in pages:
        page["backlinks"] = sorted(set(backlink_map[page["id"]]))

    root_id = choose_root(pages, by_title, by_stem)
    data = {
        "generated_at": "local",
        "root_id": root_id,
        "pages": pages,
        "edges": edges,
        "counts": count_by_folder(pages),
        "domains": build_domain_index(pages),
        "systems": count_by_system(pages),
        "topic_maps": [page["id"] for page in pages if page.get("is_topic_map")],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    copied = sync_content(pages)
    print(f"wrote {OUTPUT} ({len(pages)} pages, {len(edges)} edges)")
    print(f"synced {CONTENT_OUTPUT} ({copied} markdown files)")
    return 0


def sync_content(pages: list[dict]) -> int:
    web_root = (ROOT / "web").resolve()
    target_root = CONTENT_OUTPUT.resolve()
    if web_root not in target_root.parents:
        raise RuntimeError(f"refuse to sync outside web root: {target_root}")
    if CONTENT_OUTPUT.exists():
        shutil.rmtree(CONTENT_OUTPUT)
    copied = 0
    for page in pages:
        rel_path = page.get("path", "")
        if not rel_path.endswith(".md"):
            continue
        source = ROOT / rel_path
        if not source.exists():
            continue
        target = CONTENT_OUTPUT / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    return copied


def parse_page(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(text)
    title = frontmatter.get("title") or path.stem
    page_type = frontmatter.get("type") or infer_type(path.parent.name)
    tags = frontmatter.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    domain = frontmatter.get("domain") or infer_domain(path, tags)
    system = frontmatter.get("system") or infer_system(path, tags, domain, title)
    systems = ensure_list(frontmatter.get("systems", []))
    if not systems:
        systems = [system]
    elif system not in systems:
        systems.insert(0, system)
    note_type = frontmatter.get("note_type") or page_type
    wikilinks = unique(WIKILINK_RE.findall(text))
    headings = extract_headings(body)
    checklist = extract_checklist(body)
    search_text = extract_search_text(body)
    return {
        "id": make_id(path),
        "title": title,
        "path": path.relative_to(ROOT).as_posix(),
        "folder": path.parent.name,
        "type": page_type,
        "domain": domain,
        "system": system,
        "systems": systems,
        "note_type": note_type,
        "status": frontmatter.get("status", ""),
        "evidence_level": frontmatter.get("evidence_level", ""),
        "confidence": frontmatter.get("confidence", frontmatter.get("evidence_level", "")),
        "execution_permission": frontmatter.get("execution_permission", ""),
        "map_role": frontmatter.get("map_role", ""),
        "tags": tags,
        "topics": ensure_list(frontmatter.get("topics", [])),
        "related_questions": ensure_list(frontmatter.get("related_questions", [])),
        "source_links": frontmatter.get("source_links", []),
        "wikilinks": wikilinks,
        "headings": headings,
        "checklist": checklist,
        "summary": extract_summary(body),
        "search_text": search_text,
        "updated": frontmatter.get("updated", ""),
        "created": frontmatter.get("created", ""),
        "is_topic_map": is_topic_map(title, page_type, tags, frontmatter),
    }


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip().splitlines()
    body = text[end + 4 :].lstrip()
    return parse_simple_yaml(raw), body


def parse_simple_yaml(lines: list[str]) -> dict:
    data: dict[str, object] = {}
    key = None
    for line in lines:
        if not line.strip():
            continue
        if line.startswith("  - ") and key:
            data.setdefault(key, [])
            value = clean_yaml_value(line[4:])
            if isinstance(data[key], list):
                data[key].append(value)
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            data[key] = [] if value == "" else clean_yaml_value(value)
    return data


def clean_yaml_value(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return value


def infer_type(folder: str) -> str:
    return {
        "概念": "concept",
        "股票": "stock",
        "策略": "strategy",
        "模式": "pattern",
        "错误": "mistake",
        "sources": "source",
        "raw": "raw",
        "reports": "report",
        "reviews": "review",
    }.get(folder, "note")


def infer_domain(path: Path, tags: list[str]) -> str:
    tag_text = " ".join(tags).lower()
    if path.parent.name in KNOWLEDGE_FOLDERS or "trading/" in tag_text:
        return "交易"
    if path.parent.name in AUDIT_FOLDERS:
        return "交易"
    return "未分类"


def infer_system(path: Path, tags: list[str], domain: str, title: str) -> str:
    if domain == "交易":
        return "产业系统"
    if domain == "心理学":
        return "认知系统"
    if domain == "脑科学":
        return "认知系统"
    if domain == "佛学":
        return "意义系统"
    if domain in {
        "认知系统",
        "智能系统",
        "产业系统",
        "财富系统",
        "生命系统",
        "物理系统",
        "美学系统",
        "意义系统",
        "范式系统",
    }:
        return domain
    title_text = title.lower()
    tag_text = " ".join(tags).lower()
    if any(keyword in title for keyword in ["产业链", "国产替代", "生态", "供应链"]):
        return "产业系统"
    if "ai" in title_text or "agent" in title_text or "ai" in tag_text:
        return "智能系统"
    if any(keyword in title for keyword in ["医药", "创新药", "药", "医疗", "生物"]):
        return "生命系统"
    if any(keyword in title for keyword in ["宏观", "流动性", "周期", "商品", "价格", "涨价", "股票", "策略", "模式", "错误"]):
        return "财富系统"
    if any(keyword in title for keyword in ["机器人", "半导体", "材料", "有色", "能源", "电力", "PCB", "CPO", "MLCC", "HBM", "封装", "设备", "制造", "铜", "铝", "稀土"]):
        return "物理系统"
    if any(keyword in title for keyword in ["应用层"]):
        return "产业系统"
    return domain


def ensure_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value in ("", None):
        return []
    return [str(value)]


def is_topic_map(title: str, page_type: str, tags: list[str], frontmatter: dict) -> bool:
    if page_type == "index":
        return True
    if frontmatter.get("map_role"):
        return True
    if any(tag.endswith("map-root") or "supply-chain-map" in tag for tag in tags):
        return True
    return title.endswith("地图") or title.endswith("全景") or "地图" in title


def choose_root(pages: list[dict], by_title: dict[str, str], by_stem: dict[str, str]) -> str | None:
    preferred = by_title.get("个人知识库总览") or by_stem.get("个人知识库总览")
    if preferred:
        return preferred
    for page in pages:
        if page.get("map_role") == "root":
            return page["id"]
    return by_title.get("AI全产业链地图") or by_stem.get("AI全产业链地图") or (pages[0]["id"] if pages else None)


def make_id(path: Path) -> str:
    return path.relative_to(ROOT).as_posix().replace("/", "::").replace(".md", "")


def extract_headings(body: str) -> list[dict[str, object]]:
    headings = []
    for line in body.splitlines():
        match = re.match(r"^(#{1,4})\s+(.+?)\s*$", line)
        if match:
            headings.append({"level": len(match.group(1)), "title": match.group(2)})
    return headings


def extract_checklist(body: str) -> list[dict[str, object]]:
    items = []
    for line in body.splitlines():
        match = re.match(r"^-\s+\[([ xX])\]\s+(.+?)\s*$", line.strip())
        if match:
            items.append({"done": match.group(1).lower() == "x", "text": match.group(2)})
    return items[:40]


def extract_summary(body: str) -> str:
    lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("|") or stripped.startswith(">") or stripped.startswith("- "):
            continue
        lines.append(stripped)
        if len("".join(lines)) > 160:
            break
    return " ".join(lines)[:260]


def extract_search_text(body: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " ", body)
    text = re.sub(r"!\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(
        r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]",
        lambda match: match.group(2) or match.group(1),
        text,
    )
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 \2", text)
    text = re.sub(r"^[#>\-\*\s`|:]+", " ", text, flags=re.MULTILINE)
    text = re.sub(r"[\*_`~#>|]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50000]


def count_by_folder(pages: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for page in pages:
        counts[page["folder"]] = counts.get(page["folder"], 0) + 1
    return counts


def count_by_key(pages: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for page in pages:
        value = page.get(key) or "未分类"
        counts[value] = counts.get(value, 0) + 1
    return counts


def build_domain_index(pages: list[dict]) -> list[dict[str, object]]:
    result = []
    for domain in DEFAULT_DOMAINS:
        if domain == "全部":
            count = len(pages)
        else:
            count = sum(
                1
                for page in pages
                if page.get("domain") == domain or page.get("system") == domain or domain in page.get("systems", [])
            )
        result.append({"name": domain, "count": count})
    return result


def count_by_system(pages: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for page in pages:
        systems = page.get("systems") or [page.get("system") or "未分类"]
        for system in systems:
            counts[system] = counts.get(system, 0) + 1
    return counts


def unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
