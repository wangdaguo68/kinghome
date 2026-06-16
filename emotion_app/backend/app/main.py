import gzip
import subprocess
from glob import glob

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from httpx import HTTPError

from .db import (
    add_resonance_reaction,
    consume_quota,
    create_resonance_note,
    ensure_user,
    init_db,
    random_resonance_note,
)
from .deepseek_client import DeepSeekClient, fallback_summary
from .models import (
    AnonymousRegisterRequest,
    AnonymousRegisterResponse,
    ChatRequest,
    ChatResponse,
    ResonanceNoteCreateRequest,
    ResonanceNoteCreateResponse,
    ResonanceNoteResponse,
    ResonanceReactionRequest,
    ResonanceReactionResponse,
    SummaryRequest,
    SummaryResponse,
)
from .safety import SAFETY_REPLY, has_safety_risk

app = FastAPI(title="不想说 AI 代理", version="0.1.0")
client = DeepSeekClient()


def _count_downloads(download_path: str) -> int:
    try:
        result = subprocess.run(
            f"grep -h 'GET {download_path}' /var/log/nginx/access.log* 2>/dev/null | wc -l",
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return int(result.stdout.strip() or "0")
    except (OSError, ValueError, subprocess.SubprocessError):
        pass

    total = 0
    for log_path in glob("/var/log/nginx/access.log*"):
        opener = gzip.open if log_path.endswith(".gz") else open
        try:
            with opener(log_path, "rt", encoding="utf-8", errors="ignore") as file:
                for line in file:
                    if f"GET {download_path}" in line:
                        total += 1
        except OSError:
            continue
    return total

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    init_db()


@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {
        "ok": True,
        "model": client.model,
        "deepseek_configured": client.configured,
    }


@app.get("/api/stats/downloads")
async def download_stats() -> dict[str, int]:
    return {"downloads": _count_downloads("/download/app.apk")}


@app.get("/api/stats/downloads/cultura")
async def cultura_download_stats() -> dict[str, int]:
    return {"downloads": _count_downloads("/download/cultura.apk")}


@app.post("/api/auth/anonymous", response_model=AnonymousRegisterResponse)
async def anonymous_auth(
    request: AnonymousRegisterRequest,
) -> AnonymousRegisterResponse:
    profile = ensure_user(request.user_id)
    return AnonymousRegisterResponse(**profile)


@app.post("/api/chat/send", response_model=ChatResponse)
async def send_chat(request: ChatRequest) -> ChatResponse:
    if has_safety_risk(request.message):
        return ChatResponse(reply=SAFETY_REPLY, safety_triggered=True)

    allowed, remaining = consume_quota(request.user_id)
    if not allowed:
        return ChatResponse(
            reply="今天的免费 AI 回复已经用完了。你刚才写下的话已经保存在这里，明天可以继续慢慢说。",
            quota_exceeded=True,
            quota_remaining=0,
        )

    try:
        reply = await client.chat(request.mood_label, request.message, request.reply_mode)
        return ChatResponse(
            reply=reply,
            fallback=not client.configured,
            quota_remaining=remaining,
        )
    except HTTPError:
        return ChatResponse(
            reply="我这边刚刚有点没接住，你可以再发一次。刚才的话已经先帮你放在这里了。",
            fallback=True,
            quota_remaining=remaining,
        )


@app.post("/api/emotion-record/summary", response_model=SummaryResponse)
async def summarize(request: SummaryRequest) -> SummaryResponse:
    if has_safety_risk(request.conversation_text):
        return SummaryResponse(
            keywords=["需要陪伴", "高风险", "需要帮助"],
            emotion_color="深蓝灰",
            intensity="较强",
            summary="你现在的状态值得被认真陪伴。请尽快联系身边可信任的人，让现实中的人陪在你身边。",
            comfort_sentence="先让一个真实的人陪着你。",
            surface_emotion="强烈痛苦",
            real_pain_point="现在需要现实中的支持",
            hidden_need="安全和陪伴",
            small_action="马上联系一个可信任的人",
            self_comfort_sentence="你不需要一个人扛着。",
        )

    try:
        return await client.summary(request.conversation_text)
    except HTTPError:
        return fallback_summary()


@app.post("/api/resonance/notes", response_model=ResonanceNoteCreateResponse)
async def create_note(
    request: ResonanceNoteCreateRequest,
) -> ResonanceNoteCreateResponse:
    content = request.content.strip()
    if has_safety_risk(content):
        return ResonanceNoteCreateResponse(
            note=None,
            safety_triggered=True,
            message="这张纸条里有一些需要被认真照看的危险信号，我先不把它投出去。请优先联系身边可信任的人。",
        )
    note = create_resonance_note(
        user_id=request.user_id,
        mood_label=request.mood_label,
        content=content,
    )
    return ResonanceNoteCreateResponse(
        note=ResonanceNoteResponse(**note),
        message="这张同频纸条已经被轻轻放出去了。",
    )


@app.get("/api/resonance/notes/next", response_model=ResonanceNoteResponse | None)
async def next_note(user_id: str, mood_label: str | None = None) -> ResonanceNoteResponse | None:
    note = random_resonance_note(user_id=user_id, mood_label=mood_label)
    if note is None:
        return None
    return ResonanceNoteResponse(**note)


@app.post(
    "/api/resonance/notes/{note_id}/react",
    response_model=ResonanceReactionResponse,
)
async def react_to_note(
    note_id: str,
    request: ResonanceReactionRequest,
) -> ResonanceReactionResponse:
    try:
        reactions = add_resonance_reaction(
            note_id=note_id,
            user_id=request.user_id,
            reaction=request.reaction,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unsupported reaction") from exc
    return ResonanceReactionResponse(note_id=note_id, reactions=reactions)
