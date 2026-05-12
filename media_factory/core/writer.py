from datetime import datetime
from pathlib import Path


def write_platform_content(
    body: str,
    title: str,
    platform: str,
    output_dir: str | Path,
    hashtags: list[str] | None = None,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = "".join(c if c.isalnum() or c in "._- " else "" for c in title)
    slug = "_".join(slug.split())[:30] or "content"
    filename = f"{platform}_{date_str}_{slug}.md"
    filepath = output_dir / filename

    parts = []
    if title:
        parts.append(f"# {title}\n")
    parts.append(body)
    if hashtags:
        parts.append("\n\n" + " ".join(hashtags))
    parts.append(f"\n\n---\n*Generated at {datetime.now().isoformat()}*")

    filepath.write_text("".join(parts), encoding="utf-8")
    return filepath


def write_all_contents(results: list[dict], output_dir: str | Path) -> list[Path]:
    paths = []
    for r in results:
        path = write_platform_content(
            body=r["body"],
            title=r.get("title", ""),
            platform=r["platform"],
            output_dir=output_dir,
            hashtags=r.get("hashtags"),
        )
        paths.append(path)
    return paths
