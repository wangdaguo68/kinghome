import uuid
from fastapi import APIRouter, Depends, Query

from app.schemas import APIResponse, StorySummary
from app.middleware.auth import get_current_user

router = APIRouter()

# Seed data for dev
_SEED_STORIES = [
    {
        "id": str(uuid.uuid4()),
        "title": "郑和下西洋",
        "title_en": "Zheng He's Voyages",
        "era": "ming_dynasty",
        "region": "China",
        "cefr_level": "B1",
        "summary": "1405年，明成祖派遣郑和率领庞大的船队远航西洋...",
        "chapter_count": 5,
        "cover_emoji": "🏯",
        "tags": ["航海", "明朝", "外交", "贸易"],
    },
    {
        "id": str(uuid.uuid4()),
        "title": "The Declaration of Independence",
        "title_en": "独立宣言",
        "era": "modern",
        "region": "United States",
        "cefr_level": "A2",
        "summary": "In the summer of 1776, delegates gathered in Philadelphia...",
        "chapter_count": 5,
        "cover_emoji": "🗽",
        "tags": ["independence", "revolution", "founding fathers"],
    },
    {
        "id": str(uuid.uuid4()),
        "title": "百家争鸣：孔子的时代",
        "title_en": "The Age of Confucius",
        "era": "pre_qin",
        "region": "China",
        "cefr_level": "C1",
        "summary": "春秋末期，礼崩乐坏，孔子周游列国传播仁与礼的思想...",
        "chapter_count": 8,
        "cover_emoji": "🏛️",
        "tags": ["哲学", "先秦", "儒家", "思想"],
    },
    {
        "id": str(uuid.uuid4()),
        "title": "丝绸之路上的商人",
        "title_en": "Merchants of the Silk Road",
        "era": "han_dynasty",
        "region": "China_Central_Asia",
        "cefr_level": "B2",
        "summary": "公元前2世纪，张骞出使西域开辟丝绸之路...",
        "chapter_count": 6,
        "cover_emoji": "🐫",
        "tags": ["贸易", "汉朝", "探险", "文化交流"],
    },
    {
        "id": str(uuid.uuid4()),
        "title": "The Industrial Revolution",
        "title_en": "工业革命",
        "era": "modern",
        "region": "United_Kingdom",
        "cefr_level": "B2",
        "summary": "From the steam engine to the factory system...",
        "chapter_count": 4,
        "cover_emoji": "🏭",
        "tags": ["industry", "technology", "social change"],
    },
]


@router.get("")
async def list_stories(
    era: str | None = Query(None),
    level: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    stories = _SEED_STORIES
    if era:
        stories = [s for s in stories if s["era"] == era]
    if level:
        stories = [s for s in stories if s["cefr_level"] == level]

    start = (page - 1) * page_size
    items = stories[start : start + page_size]
    return APIResponse(data={"items": items, "total": len(stories), "page": page, "page_size": page_size})


@router.get("/{story_id}")
async def get_story(story_id: str, user: dict = Depends(get_current_user)):
    for s in _SEED_STORIES:
        if s["id"] == story_id:
            return APIResponse(data=s)
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Story not found")


@router.get("/{story_id}/chapters/{chapter_index}")
async def get_chapter(story_id: str, chapter_index: int, user: dict = Depends(get_current_user)):
    from fastapi import HTTPException

    story = next((s for s in _SEED_STORIES if s["id"] == story_id), None)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if chapter_index < 0 or chapter_index >= story["chapter_count"]:
        raise HTTPException(status_code=404, detail="Chapter not found")

    from app.gateway.router import router as model_router, StoryPrompt

    prompt = StoryPrompt(
        era=story["era"],
        region=story["region"],
        level=story["cefr_level"],
        lang="zh",
        chapter=chapter_index + 1,
    )
    try:
        chapter = await model_router.generate_story_chapter(
            prompt, user["sub"], user.get("plan", "free"), user.get("model_preference")
        )
    except Exception as e:
        chapter = {
            "title": f"Chapter {chapter_index + 1}",
            "title_en": f"Chapter {chapter_index + 1}",
            "content_original": f"[AI generation pending: {e}]",
            "content_translation": "",
            "vocabulary": [],
            "cultural_notes": [],
        }

    chapter["id"] = f"{story_id}_ch{chapter_index}"
    chapter["number"] = chapter_index
    return APIResponse(data=chapter)
