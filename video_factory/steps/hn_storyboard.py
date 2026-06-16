#!/usr/bin/env python3
"""Create a Hacker News short-video storyboard and TTS audio."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


def fetch_json(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={"User-Agent": "VideoFactory/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title or "").strip()
    return title.rstrip(".")


def source_label(url: str) -> str:
    host = urlparse(url or "").netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "news.ycombinator.com"


def split_captions(text: str, max_len: int = 24) -> list[str]:
    parts = re.split(r"([，。！？；])", text)
    sentences = []
    for i in range(0, len(parts), 2):
        chunk = parts[i].strip()
        punct = parts[i + 1] if i + 1 < len(parts) else ""
        if chunk:
            sentences.append(chunk + punct)

    captions: list[str] = []
    for sentence in sentences:
        while len(sentence) > max_len:
            cut = sentence.rfind("，", 0, max_len)
            if cut <= 0:
                cut = sentence.rfind(" ", 0, max_len)
            if cut <= 0:
                cut = max_len
            captions.append(sentence[:cut].strip(" ，"))
            sentence = sentence[cut:].strip(" ，")
        if sentence:
            captions.append(sentence)
    return captions


def image_prompt(title: str, index: int, source: str) -> str:
    styles = [
        "documentary newsroom desk photo",
        "muted editorial technology still life",
        "realistic analyst workspace photograph",
        "quiet product research desk scene",
        "natural light tech reporting photo",
    ]
    return (
        f"{styles[index % len(styles)]}, inspired by the news topic: {clean_title(title)}. "
        f"Subtle visual hint of {source}; vertical 9:16, realistic lighting, restrained colors, "
        "credible news-magazine style, no readable text, no logos, no watermark, no sci-fi glow, "
        "no exaggerated AI-art effects"
    )


def pick_items(limit: int, count: int) -> list[dict]:
    ids = fetch_json(HN_TOP)[:limit]
    items = []
    for item_id in ids:
        try:
            item = fetch_json(HN_ITEM.format(id=item_id), timeout=10)
        except Exception as exc:
            print(f"skip {item_id}: {exc}", file=sys.stderr)
            continue
        if item and item.get("type") == "story" and item.get("title"):
            score = int(item.get("score") or 0)
            comments = int(item.get("descendants") or 0)
            item["_rank_score"] = score + comments * 2
            items.append(item)
    items.sort(key=lambda x: x.get("_rank_score", 0), reverse=True)
    return items[:count]


def build_segments(items: list[dict], duration: int) -> list[dict]:
    target = max(30, min(60, duration))
    segments = [
        {
            "title": "Hacker News 今日热点",
            "source_label": "news.ycombinator.com",
            "narration": f"今天从 Hacker News 前一百条里，挑出 {len(items)} 条开发者正在讨论的新闻。",
            "image_prompt": (
                "Realistic editorial photo of a laptop showing an abstract news dashboard, "
                "developer desk at dusk, restrained newsroom look, vertical 9:16, no readable text, "
                "no logos, no watermark, no sci-fi glow"
            ),
            "duration_est": min(6.0, target / (len(items) + 1)),
        }
    ]
    for idx, item in enumerate(items):
        title = clean_title(item.get("title", ""))
        score = int(item.get("score") or 0)
        comments = int(item.get("descendants") or 0)
        src = source_label(item.get("url", ""))
        narration = (
            f"第 {idx + 1} 条，看屏幕上的标题。"
            f"来源是 {src}，HN 热度 {score} 分，约 {comments} 条讨论。"
        )
        segments.append({
            "title": title,
            "source_label": src,
            "narration": narration,
            "image_prompt": image_prompt(title, idx, src),
            "duration_est": 8.0,
            "hn_id": item.get("id"),
            "hn_url": f"https://news.ycombinator.com/item?id={item.get('id')}",
            "source_url": item.get("url", ""),
            "score": score,
            "comments": comments,
        })

    for seg in segments:
        seg["caption_chunks"] = split_captions(seg["narration"])
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
    p = argparse.ArgumentParser()
    p.add_argument("--topic", default="Hacker News 热点")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--duration", type=int, default=60)
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    p.add_argument("--rate", default="+8%")
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    items = pick_items(args.limit, args.count)
    if not items:
        raise SystemExit("No Hacker News items fetched")

    (out_dir / "news_items.json").write_text(
        json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    segments = build_segments(items, args.duration)

    for idx, seg in enumerate(segments):
        audio_path = out_dir / f"seg_{idx:02d}.mp3"
        tts(seg["narration"], audio_path, args.voice, args.rate)
        duration = audio_duration(audio_path)
        seg["audio_path"] = str(audio_path.resolve())
        seg["audio_duration"] = duration
        seg["duration_est"] = round(duration + 0.6, 2)

    segments_path = out_dir / "segments.json"
    segments_path.write_text(json.dumps(segments, indent=2, ensure_ascii=False), encoding="utf-8")
    print(str(segments_path.resolve()))


if __name__ == "__main__":
    main()
