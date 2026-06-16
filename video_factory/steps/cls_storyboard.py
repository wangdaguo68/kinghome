#!/usr/bin/env python3
"""Create a short-video storyboard from CLS telegraph hot news."""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import urllib.request
from pathlib import Path


CLS_TELEGRAPH = "https://www.cls.cn/telegraph"


def fetch_page(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


def extract_next_data(page: str) -> dict:
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        page,
        re.S,
    )
    if not match:
        raise SystemExit("Cannot find CLS __NEXT_DATA__ payload")
    return json.loads(html.unescape(match.group(1)))


def clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def title_from_content(content: str) -> str:
    content = clean_text(content)
    match = re.match(r"【(.+?)】", content)
    if match:
        return match.group(1).strip()
    content = re.sub(r"^财联社\d+月\d+日电，?", "", content)
    return content[:38].rstrip("，。；")


def summary_from_content(content: str, title: str) -> str:
    content = clean_text(content)
    content = re.sub(r"^【.+?】", "", content)
    content = re.sub(r"^财联社\d+月\d+日电，?", "", content)
    content = re.sub(r"^《科创板日报》\d+日讯，?", "", content)
    content = content.strip(" ，。")
    if not content:
        return title
    if len(content) <= 48:
        return content.rstrip("，。；")
    cut = content.rfind("，", 0, 48)
    if cut < 18:
        cut = content.rfind("。", 0, 56)
    if cut < 18:
        return title
    return content[:cut].rstrip("，。；：《（(、") + "。"


def compact_for_speech(text: str, limit: int = 22) -> str:
    text = clean_text(text)
    for punct in "。；！？":
        pos = text.find(punct)
        if 6 <= pos <= limit + 8:
            text = text[:pos]
            break
    if len(text) > limit:
        cut = text.rfind("，", 0, limit)
        if cut < 6:
            cut = limit
        text = text[:cut]
    text = text.rstrip(" ，。；：《（(、")
    text = re.sub(r"[《（(][^》）)]*$", "", text).rstrip(" ，。；：")
    return text or "信息仍在更新"


def split_captions(text: str, max_len: int = 22) -> list[str]:
    parts = re.split(r"([，。！？；])", text)
    captions: list[str] = []
    for i in range(0, len(parts), 2):
        sentence = (parts[i] + (parts[i + 1] if i + 1 < len(parts) else "")).strip()
        while len(sentence) > max_len:
            cut = sentence.rfind("，", 0, max_len)
            if cut <= 0:
                cut = max_len
            captions.append(sentence[:cut].strip(" ，"))
            sentence = sentence[cut:].strip(" ，")
        if sentence:
            captions.append(sentence)
    return captions


def classify(title: str, summary: str) -> str:
    text = title + summary
    if any(word in text for word in ("机器人", "算力", "服务器", "DeepSeek", "模型", "AI", "人工智能", "光模块", "PCB", "思科", "宕机", "数据中心")):
        return "科技"
    if any(word in text for word in ("收购", "股权", "控制权", "减持", "复牌", "交易", "排他性谈判", "恒大物业")):
        return "公司"
    if any(word in text for word in ("镍", "大宗商品", "煤炭", "原油", "美元/吨")):
        return "商品"
    if any(word in text for word in ("伊朗", "印尼", "印度尼西亚", "韩国", "航线", "口岸", "泰国", "以色列", "黎巴嫩", "叙利亚", "法国", "G-7", "七国集团")):
        return "全球"
    if any(word in text for word in ("医保", "支架", "临床", "集采", "就业", "ADP", "美国私营部门")):
        return "宏观"
    if any(word in text for word in ("一人公司", "奖励", "海南", "政策")):
        return "民生"
    return "市场"


def narration_for(item: dict, idx: int) -> str:
    title = item["title"]
    summary = item["summary"]
    category = classify(title, summary)
    short_summary = compact_for_speech(summary, 22)
    openings = {
        "科技": ["科技产业线继续更新。", "数字基础设施成本被重新定价。"],
        "公司": ["公司交易进展出现变化。", "个股公告释放新信息。"],
        "商品": ["商品市场有新信号。", "资源品价格继续波动。"],
        "全球": ["海外消息值得留意。", "全球市场变量继续增加。"],
        "民生": ["地方政策释放新信号。", "区域扶持政策继续加码。"],
        "宏观": ["宏观数据出现新读数。", "海外就业数据带来新参考。"],
        "市场": ["市场焦点继续切换。", "盘后消息面继续更新。"],
    }
    tails = [
        "后续看市场反应。",
        "短线看公告反馈。",
        "相关板块可能继续发酵。",
        "细节披露后影响会更清楚。",
        "先看情绪，再看交易线索。"
    ]
    opening = openings[category][idx % len(openings[category])]
    return f"{opening}要点是，{short_summary}。{tails[idx % len(tails)]}"


def image_prompt(title: str, summary: str, index: int) -> str:
    category = classify(title, summary)
    visual_map = {
        "科技": "robotics lab, server room, and AI product research desk",
        "公司": "corporate acquisition documents, boardroom table, and market report",
        "商品": "commodity trading desk, metals chart, port logistics, analyst notes",
        "全球": "geopolitical risk map, international business newsroom, logistics desk",
        "民生": "healthcare policy desk, hospital procurement files, public policy report",
        "宏观": "macroeconomic data desk, labor market chart, central bank briefing notes",
        "市场": "Chinese financial newsroom, analyst workstation, market dashboard",
    }
    return (
        f"Realistic finance-news editorial photo about: {title}. "
        f"Visual direction: {visual_map[category]}. "
        "Vertical 9:16, documentary lighting, restrained colors, credible Chinese business media style, "
        "real objects and desks, no readable text, no logos, no watermark, no sci-fi glow, "
        "no exaggerated AI-art effects"
    )


def pick_items(limit: int, count: int) -> list[dict]:
    page = fetch_page(CLS_TELEGRAPH)
    data = extract_next_data(page)
    items = data["props"]["initialState"]["telegraph"]["telegraphList"][:limit]
    clean_items = []
    for item in items:
        if item.get("is_ad"):
            continue
        content = clean_text(item.get("content", ""))
        if not content:
            continue
        title = clean_text(item.get("title") or "") or title_from_content(content)
        summary = summary_from_content(content, title)
        clean_items.append(
            {
                "id": item.get("id"),
                "title": title,
                "summary": summary,
                "content": content,
                "reading_num": int(item.get("reading_num") or 0),
                "comment_num": int(item.get("comment_num") or 0),
                "ctime": item.get("ctime"),
                "shareurl": item.get("shareurl") or CLS_TELEGRAPH,
            }
        )
    clean_items.sort(key=lambda x: (x["reading_num"], x["comment_num"]), reverse=True)
    return clean_items[:count]


def build_segments(items: list[dict]) -> list[dict]:
    segments = []
    for idx, item in enumerate(items):
        narration = narration_for(item, idx)
        heat = f"阅读 {item['reading_num']:,}".replace(",", ",")
        segment = {
            "title": item["title"],
            "summary": item["summary"],
            "source_label": "财联社",
            "heat_label": heat,
            "category": classify(item["title"], item["summary"]),
            "narration": narration,
            "image_prompt": image_prompt(item["title"], item["summary"], idx),
            "duration_est": 10.5,
            "source_url": item["shareurl"],
            "score": item["reading_num"],
            "comments": item["comment_num"],
            "cls_id": item["id"],
        }
        segment["caption_chunks"] = split_captions(segment["narration"])
        segments.append(segment)
    return segments


def tts(text: str, out: Path, voice: str, rate: str) -> None:
    cmd = [
        "edge-tts",
        "--voice",
        voice,
        "--rate",
        rate,
        "--text",
        text,
        "--write-media",
        str(out),
    ]
    subprocess.run(cmd, check=True, timeout=180)


def audio_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return float(result.stdout.strip())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="财联社热点")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--duration", type=int, default=58)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    parser.add_argument("--rate", default="+18%")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    items = pick_items(args.limit, args.count)
    if not items:
        raise SystemExit("No CLS items fetched")

    (out_dir / "news_items.json").write_text(
        json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    segments = build_segments(items)

    for idx, seg in enumerate(segments):
        audio_path = out_dir / f"seg_{idx:02d}.mp3"
        tts(seg["narration"], audio_path, args.voice, args.rate)
        duration = audio_duration(audio_path)
        seg["audio_path"] = str(audio_path.resolve())
        seg["audio_duration"] = duration
        seg["duration_est"] = round(max(duration + 0.55, 10.0), 2)

    total = sum(seg["duration_est"] for seg in segments)
    if total < 50:
        pad = round((50 - total) / len(segments), 2)
        for seg in segments:
            seg["duration_est"] = round(seg["duration_est"] + pad, 2)
    elif total > args.duration:
        scale = args.duration / total
        for seg in segments:
            seg["duration_est"] = round(max(seg["audio_duration"] + 0.35, seg["duration_est"] * scale), 2)

    segments_path = out_dir / "segments.json"
    segments_path.write_text(json.dumps(segments, indent=2, ensure_ascii=False), encoding="utf-8")
    print(str(segments_path.resolve()))


if __name__ == "__main__":
    main()
