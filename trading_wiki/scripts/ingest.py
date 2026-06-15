#!/usr/bin/env python3
"""Ingest raw market information into a Markdown trading wiki.

The audit layer keeps raw/source/review/report files. The knowledge layer
materializes useful notes under Chinese folders like 概念, 股票, 策略, 模式, 错误.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from string import Template


AUDIT_DIRS = ["raw", "sources", "reviews", "reports", "templates", "scripts", "tests"]
KNOWLEDGE_DIRS = ["策略", "概念", "模式", "股票", "错误"]

PAGE_DIRS = {
    "concept": "概念",
    "stock": "股票",
    "strategy": "策略",
    "pattern": "模式",
    "mistake": "错误",
}

KIND_LABELS = {
    "concept": "概念",
    "stock": "股票",
    "strategy": "策略",
    "pattern": "模式",
    "mistake": "错误",
}

HEADING_TO_KIND = {
    "概念": "concept",
    "主题": "concept",
    "方向": "concept",
    "标的": "stock",
    "股票": "stock",
    "公司": "stock",
    "关联公司": "stock",
    "策略": "strategy",
    "模式": "pattern",
    "错误": "mistake",
    "反思": "mistake",
    "复盘": "mistake",
}

LOW_EVIDENCE_ALLOWED_PERMISSIONS = {"none", "observe_only", "needs_verification"}
ELEVATED_PERMISSIONS = {"watchlist", "candidate"}
TEMPLATE_TOKEN_RE = re.compile(r"\{\{[a-zA-Z0-9_]+\}\}")
CHECKED_CANDIDATE_RE = re.compile(r"^- \[[xX]\]\s+`(?P<kind>\w+)`\s+\|\s+(?P<title>.+?)\s*$")


@dataclass
class RenderedFile:
    path: Path
    action: str


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.command == "apply-review":
        return apply_review(root=root, review_path=Path(args.review))

    return ingest(
        root=root,
        date=args.date,
        raw_input=Path(args.input) if args.input else None,
        source_url=args.source_url,
        source_type=args.source_type,
        title=args.title,
        force=args.force,
        no_materialize=args.no_materialize,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest raw market information into a Markdown trading wiki.")
    parser.add_argument("--root", default=".", help="Wiki root directory. Defaults to current directory.")

    subparsers = parser.add_subparsers(dest="command")
    apply_parser = subparsers.add_parser("apply-review", help="Create checked candidate pages from a review file.")
    apply_parser.add_argument("--review", required=True, help="Path to the review file, relative to root or absolute.")

    parser.add_argument("--date", help="Ingest date in YYYY-MM-DD format.")
    parser.add_argument("--input", help="Raw input Markdown/text file.")
    parser.add_argument("--source-url", default="无", help="External source URL if available.")
    parser.add_argument("--source-type", default="unknown", help="Source type, such as group_chat, article, research, official.")
    parser.add_argument("--title", help="Source title. Defaults to the date.")
    parser.add_argument("--force", action="store_true", help="Overwrite audit files. Knowledge pages are appended, not overwritten.")
    parser.add_argument("--no-materialize", action="store_true", help="Only generate source/review/report; do not create knowledge notes.")
    return parser


def ingest(
    *,
    root: Path,
    date: str | None,
    raw_input: Path | None,
    source_url: str,
    source_type: str,
    title: str | None,
    force: bool,
    no_materialize: bool,
) -> int:
    if not date or not raw_input:
        print("error: --date and --input are required for ingest", file=sys.stderr)
        return 2

    try:
        validate_date(date)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    ensure_directories(root)
    raw_path = resolve_under_root(root, raw_input)
    if not raw_path.exists():
        print(f"error: raw input not found: {raw_path}", file=sys.stderr)
        return 1

    raw_text = raw_path.read_text(encoding="utf-8")
    source_hash = sha256_text(raw_text)
    source_title = title or date
    evidence_level = default_evidence_level(source_type)
    generated_at = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    candidates = extract_candidates(raw_text)
    safety_results, safety_ok = safety_check_context(evidence_level=evidence_level, candidates=candidates)

    context = {
        "title": source_title,
        "date": date,
        "generated_at": generated_at,
        "raw_path": display_path(root, raw_path),
        "source_url": source_url,
        "source_type": source_type,
        "source_hash": source_hash,
        "evidence_level": evidence_level,
        "themes": render_theme_list(candidates),
        "candidate_links": render_candidate_links(candidates),
        "raw_excerpt": excerpt(raw_text, 2400),
        "source_title": source_title,
        "review_title": f"{date} wiki-change-review",
        "review_filename": f"{date}-wiki-change-review.md",
        "concept_candidates": render_review_candidates("concept", candidates["concept"]),
        "stock_candidates": render_review_candidates("stock", candidates["stock"]),
        "strategy_candidates": render_review_candidates("strategy", candidates["strategy"]),
        "pattern_candidates": render_review_candidates("pattern", candidates["pattern"]),
        "mistake_candidates": render_review_candidates("mistake", candidates["mistake"]),
        "update_candidates": render_update_candidates(root, candidates),
        "safety_results": render_safety_results(safety_results),
    }

    rendered: list[RenderedFile] = []
    rendered.append(write_rendered(root, "templates/source.md", root / "sources" / f"{date}.md", context, force))
    rendered.append(write_rendered(root, "templates/review.md", root / "reviews" / f"{date}-wiki-change-review.md", context, force))

    if not no_materialize:
        rendered.extend(
            materialize_candidates(
                root=root,
                candidates=candidates,
                raw_text=raw_text,
                date=date,
                source_title=source_title,
                source_hash=source_hash,
                evidence_level=evidence_level,
            )
        )

    context["file_changes"] = render_file_changes(rendered)
    rendered.append(write_rendered(root, "templates/report.md", root / "reports" / f"{date}-ingest.md", context, force))

    warnings = safety_check_generated_files([item.path for item in rendered])
    if warnings:
        safety_ok = False
        print("Safety warnings:")
        for warning in warnings:
            print(f"- {warning}")

    print(f"已完成 {date} 摄入。")
    print(f"Source: {root / 'sources' / f'{date}.md'}")
    print(f"Review: {root / 'reviews' / f'{date}-wiki-change-review.md'}")
    print(f"Report: {root / 'reports' / f'{date}-ingest.md'}")
    print(f"Knowledge pages: {sum(1 for item in rendered if item.path.parent.name in KNOWLEDGE_DIRS)}")
    print(f"Safety: {'passed' if safety_ok else 'warnings'}")
    return 0 if safety_ok else 1


def apply_review(*, root: Path, review_path: Path) -> int:
    ensure_directories(root)
    review_file = resolve_under_root(root, review_path)
    if not review_file.exists():
        print(f"error: review file not found: {review_file}", file=sys.stderr)
        return 1

    review_text = review_file.read_text(encoding="utf-8")
    date = extract_frontmatter_value(review_text, "created") or dt.date.today().isoformat()
    source_title = extract_source_title(review_text) or date
    source_hash = extract_frontmatter_value(review_text, "source_hash") or ""
    evidence_level = extract_frontmatter_value(review_text, "evidence_level") or "low"

    candidates = {kind: [] for kind in PAGE_DIRS}
    for kind, title in checked_candidates(review_text):
        if kind in candidates:
            candidates[kind].append(title)

    created = materialize_candidates(
        root=root,
        candidates=candidates,
        raw_text=review_text,
        date=date,
        source_title=source_title,
        source_hash=source_hash,
        evidence_level=evidence_level,
    )

    warnings = safety_check_generated_files([item.path for item in created])
    for warning in warnings:
        print(f"warning: {warning}")

    print(f"创建或更新页面: {len(created)}")
    for item in created:
        print(f"- {item.action}: {item.path}")
    return 0 if not warnings else 1


def materialize_candidates(
    *,
    root: Path,
    candidates: dict[str, list[str]],
    raw_text: str,
    date: str,
    source_title: str,
    source_hash: str,
    evidence_level: str,
) -> list[RenderedFile]:
    rendered: list[RenderedFile] = []
    for kind, titles in candidates.items():
        for title in titles:
            target = root / PAGE_DIRS[kind] / f"{safe_filename(title)}.md"
            snippets = find_snippets(raw_text, title)
            if target.exists():
                action = append_knowledge_update(
                    target=target,
                    title=title,
                    kind=kind,
                    date=date,
                    source_title=source_title,
                    source_hash=source_hash,
                    evidence_level=evidence_level,
                    snippets=snippets,
                )
            else:
                text = render_knowledge_page(
                    title=title,
                    kind=kind,
                    date=date,
                    source_title=source_title,
                    source_hash=source_hash,
                    evidence_level=evidence_level,
                    snippets=snippets,
                )
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text.rstrip() + "\n", encoding="utf-8")
                action = "created"
            rendered.append(RenderedFile(path=target, action=action))
    return rendered


def render_knowledge_page(
    *,
    title: str,
    kind: str,
    date: str,
    source_title: str,
    source_hash: str,
    evidence_level: str,
    snippets: list[str],
) -> str:
    label = KIND_LABELS[kind]
    permission = "none" if kind == "mistake" else "observe_only"
    body = render_body_by_kind(kind, title, snippets)
    return f"""---
title: "{title}"
type: {kind}
folder: {label}
created: {date}
updated: {date}
status: active
evidence_level: {evidence_level}
execution_permission: {permission}
source_links:
  - "[[{source_title}]]"
source_hashes:
  - "{source_hash}"
tags:
  - trading/wiki/{kind}
---

# {title}

> [!warning] 证据边界
> 本页来自 [[{source_title}]] 的自动沉淀。当前证据强度为 `{evidence_level}`，执行权限为 `{permission}`。低证据只代表观察线索，不构成买卖建议。

{body}

## 当日证据摘录

{render_snippet_list(snippets)}

## 验证清单

{render_validation_list(kind)}

## 引用来源

- [[{source_title}]]
- source_hash: `{source_hash}`

## 变更记录

- {date}: 根据 [[{source_title}]] 新建{label}页。
"""


def render_body_by_kind(kind: str, title: str, snippets: list[str]) -> str:
    if kind == "concept":
        return f"""## 概念定义

{title} 是从当日产业舆情中沉淀出的交易观察概念。先把它作为低证据线索保存，后续用公告、订单、价格、产能、客户或财务数据验证。

## 与相近页面的区别

| 相近页面 | 区别 | 避免误用 |
| --- | --- | --- |
| 待补充 | 待补充 | 不把题材热度直接当成基本面兑现 |

## 产业链结构

| 环节 | 当前线索 | 需要验证 |
| --- | --- | --- |
| 需求端 | {first_snippet(snippets)} | 是否有真实下游需求、订单或价格变化 |
| 供给端 | 待补充 | 是否存在产能瓶颈、供给扰动或国产替代 |
| 标的映射 | 待补充 | 公司收入纯度、客户认证、利润弹性 |

## 关键事实与催化

| 线索 | 当前处理 | 事实强度 | L4 权限 |
| --- | --- | --- | --- |
| {title} | 观察假设 | 低 | 不单独构成买点 |
"""
    if kind == "stock":
        return f"""## 公司定位

{title} 出现在当日产业舆情标的候选中。先记录为观察标的，后续验证真实业务承接、收入纯度和利润弹性。

## 相关概念

- 待补充

## 正面逻辑

| 逻辑 | 证据 | 需要验证 |
| --- | --- | --- |
| 当日微信产业舆情提及 | {first_snippet(snippets)} | 产品、客户、订单、收入占比、价格传导 |

## 风险与反证

- 可能只是盘面标签或题材扩散，并非基本面变化。
"""
    if kind == "strategy":
        return f"""## 策略定义

{title} 是从当日舆情沉淀出的交易研究框架。

## 适用条件

- 待补充。

## 失效条件

- 线索无法被事实验证。
- 题材热度退潮但基本面没有兑现。
"""
    if kind == "pattern":
        return f"""## 模式定义

{title} 是可复用的市场认知模式。

## 触发条件

- 待补充。

## 典型路径

1. 舆情出现。
2. 盘面或产业链标签扩散。
3. 进入事实验证。
4. 决定是否升级为更高权限。
"""
    return f"""## 错误描述

{title} 是当日舆情处理中需要避免的认知错误。

## 错误机制

- 把低证据线索过早升级成事实或交易结论。

## 纠偏规则

- 先保存来源，再标注证据强度，最后做事实验证。
"""


def append_knowledge_update(
    *,
    target: Path,
    title: str,
    kind: str,
    date: str,
    source_title: str,
    source_hash: str,
    evidence_level: str,
    snippets: list[str],
) -> str:
    text = target.read_text(encoding="utf-8")
    marker = f"source_hash: `{source_hash}`"
    if marker in text:
        return "exists"

    update = f"""

## 认知更新 {date}

- 来源: [[{source_title}]]
- source_hash: `{source_hash}`
- 证据强度: {evidence_level}
- 处理方式: 追加为观察线索，等待事实验证。

### 新增证据摘录

{render_snippet_list(snippets)}
"""
    target.write_text(text.rstrip() + update + "\n", encoding="utf-8")
    return "updated"


def validate_date(value: str) -> None:
    try:
        dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("--date must use YYYY-MM-DD") from exc


def ensure_directories(root: Path) -> None:
    for name in AUDIT_DIRS + KNOWLEDGE_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)


def resolve_under_root(root: Path, path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def display_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def default_evidence_level(source_type: str) -> str:
    normalized = source_type.strip().lower()
    if normalized in {"official", "announcement", "filing", "order"}:
        return "high"
    if normalized in {"research", "media", "conference", "channel_check"}:
        return "medium"
    if normalized in {"group_chat", "rumor", "article", "social"}:
        return "low"
    return "unknown"


def extract_candidates(raw_text: str) -> dict[str, list[str]]:
    candidates = {kind: [] for kind in PAGE_DIRS}
    current_kind: str | None = None
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        is_heading = stripped.startswith("#")
        heading = stripped.lstrip("#").strip(" ：:")
        if is_heading:
            current_kind = HEADING_TO_KIND.get(heading)
            continue
        if current_kind and looks_like_list_item(stripped):
            title = normalize_candidate_title(stripped)
            if title:
                add_unique(candidates[current_kind], title)

    for explicit_kind, marker in [
        ("concept", "概念:"),
        ("stock", "标的:"),
        ("stock", "股票:"),
        ("strategy", "策略:"),
        ("pattern", "模式:"),
        ("mistake", "错误:"),
    ]:
        for title in extract_marker_values(raw_text, marker):
            add_unique(candidates[explicit_kind], title)
    return candidates


def looks_like_list_item(value: str) -> bool:
    return value.startswith(("- ", "* ", "1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. ", "9. "))


def normalize_candidate_title(value: str) -> str:
    value = re.sub(r"^[-*]\s+", "", value)
    value = re.sub(r"^\d+\.\s+", "", value)
    value = value.split("：", 1)[0].split(":", 1)[0].strip()
    value = re.sub(r"[`#\[\]]", "", value).strip()
    return value[:60].strip()


def extract_marker_values(raw_text: str, marker: str) -> list[str]:
    values: list[str] = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(marker):
            after = stripped.split(marker, 1)[1]
            for part in re.split(r"[，,、/；;]", after):
                title = part.strip(" -`[]。；;，,")
                if title:
                    values.append(title[:60])
    return values


def add_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def find_snippets(raw_text: str, title: str, limit: int = 5) -> list[str]:
    keywords = [title]
    keywords.extend([part for part in re.split(r"[ /+与和、（）()]", title) if len(part) >= 2])
    snippets: list[str] = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if any(keyword and keyword in stripped for keyword in keywords):
            clean = re.sub(r"^[-*]\s+", "", stripped)
            clean = re.sub(r"^\d+\.\s+", "", clean)
            add_unique(snippets, clean[:240])
        if len(snippets) >= limit:
            break
    return snippets or ["待从来源中补充更精确的证据摘录。"]


def first_snippet(snippets: list[str]) -> str:
    return snippets[0] if snippets else "待补充"


def render_snippet_list(snippets: list[str]) -> str:
    return "\n".join(f"- {snippet}" for snippet in snippets)


def render_validation_list(kind: str) -> str:
    if kind == "concept":
        return "\n".join(
            [
                "- [ ] 是否有公告、订单、价格、产能、客户或财务验证。",
                "- [ ] 是否能和相近概念区分。",
                "- [ ] 是否能映射到具体公司收入或利润弹性。",
            ]
        )
    if kind == "stock":
        return "\n".join(
            [
                "- [ ] 是否真实承接相关产品或产业链环节。",
                "- [ ] 收入占比、客户认证、订单和价格是否可验证。",
                "- [ ] 是否存在题材标签误配。",
            ]
        )
    return "- [ ] 后续用更多 source archive 验证或修正。"


def render_theme_list(candidates: dict[str, list[str]]) -> str:
    themes = candidates["concept"] + candidates["pattern"] + candidates["strategy"]
    if not themes:
        return "- 待人工从 raw 输入中提炼主题。"
    return "\n".join(f"- {item}" for item in themes)


def render_candidate_links(candidates: dict[str, list[str]]) -> str:
    rows: list[str] = []
    for kind, titles in candidates.items():
        for title in titles:
            rows.append(f"- `{kind}` [[{title}]]")
    return "\n".join(rows) if rows else "- 暂无自动识别候选项，请在 review 文件中人工补充。"


def render_review_candidates(kind: str, titles: list[str]) -> str:
    if not titles:
        return f"- [ ] `{kind}` | 待人工补充"
    return "\n".join(f"- [ ] `{kind}` | {title}" for title in titles)


def render_update_candidates(root: Path, candidates: dict[str, list[str]]) -> str:
    matches: list[str] = []
    for kind, titles in candidates.items():
        directory = root / PAGE_DIRS[kind]
        for title in titles:
            target = directory / f"{safe_filename(title)}.md"
            if target.exists():
                matches.append(f"- [ ] `{kind}` | [[{target.stem}]] | 将追加新证据")
    return "\n".join(matches) if matches else "- 暂未发现与候选项同名的旧页面。"


def render_safety_results(results: list[tuple[str, bool, str]]) -> str:
    lines = []
    for name, ok, detail in results:
        mark = "x" if ok else " "
        lines.append(f"- [{mark}] {name}: {detail}")
    return "\n".join(lines)


def render_file_changes(files: list[RenderedFile]) -> str:
    return "\n".join(f"| {item.path.parent.name} | `{item.path.as_posix()}` | {item.action} |" for item in files)


def safety_check_context(*, evidence_level: str, candidates: dict[str, list[str]]) -> tuple[list[tuple[str, bool, str]], bool]:
    results = [
        ("low evidence permission gate", True, "低证据默认只允许 observe_only"),
        ("candidate extraction", True, f"识别候选项 {sum(len(v) for v in candidates.values())} 个"),
        ("source link policy", True, "所有生成页面都会链接 source archive"),
    ]
    if evidence_level == "low":
        permission = "observe_only"
        ok = permission in LOW_EVIDENCE_ALLOWED_PERMISSIONS
        results[0] = ("low evidence permission gate", ok, f"低证据默认权限为 {permission}")
    return results, all(item[1] for item in results)


def safety_check_generated_files(paths: list[Path]) -> list[str]:
    warnings: list[str] = []
    for path in paths:
        if not path.exists():
            warnings.append(f"missing generated file: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if TEMPLATE_TOKEN_RE.search(text):
            warnings.append(f"unresolved template token in {path}")
        if "evidence_level: low" in text:
            permission = extract_frontmatter_value(text, "execution_permission")
            if permission in ELEVATED_PERMISSIONS:
                warnings.append(f"low evidence has elevated permission in {path}")
        page_type = extract_frontmatter_value(text, "type")
        if page_type in PAGE_DIRS and "source_links:" not in text and "## 引用来源" not in text:
            warnings.append(f"page missing source link section: {path}")
    return warnings


def write_rendered(root: Path, template_rel: str, target: Path, context: dict[str, str], force: bool) -> RenderedFile:
    template_path = root / template_rel
    template = template_path.read_text(encoding="utf-8")
    rendered = render_template(template, context)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and not force:
        return RenderedFile(path=target, action="exists")

    action = "updated" if target.exists() else "created"
    target.write_text(rendered.rstrip() + "\n", encoding="utf-8")
    return RenderedFile(path=target, action=action)


def render_template(template: str, context: dict[str, str]) -> str:
    converted = re.sub(r"\{\{([a-zA-Z0-9_]+)\}\}", r"${\1}", template)
    return Template(converted).safe_substitute(context)


def excerpt(text: str, length: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= length:
        return cleaned
    return cleaned[:length].rstrip() + "\n..."


def checked_candidates(review_text: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for line in review_text.splitlines():
        match = CHECKED_CANDIDATE_RE.match(line.strip())
        if match:
            items.append((match.group("kind"), match.group("title").strip()))
    return items


def extract_frontmatter_value(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*\"?(.*?)\"?\s*$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def extract_source_title(review_text: str) -> str | None:
    match = re.search(r"Source archive:\s+\[\[(.+?)\]\]", review_text)
    return match.group(1).strip() if match else None


def safe_filename(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:100] or "untitled"


if __name__ == "__main__":
    raise SystemExit(main())
