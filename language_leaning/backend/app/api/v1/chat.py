import uuid
from fastapi import APIRouter, Depends, HTTPException

from app.schemas import APIResponse, ChatStartRequest, ChatMessageRequest
from app.middleware.auth import get_current_user
from app.gateway.router import router as model_router, QuotaExceededError

router = APIRouter()

_sessions: dict[str, dict] = {}


@router.post("/start")
async def start_chat(data: ChatStartRequest, user: dict = Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "story_id": data.story_id,
        "character": data.character,
        "messages": [{"role": "system", "content": f"Roleplay as {data.character}"}],
    }

    character_context = f"Historical character: {data.character} from story {data.story_id}"
    try:
        greeting = await model_router.chat(
            messages=[{"role": "user", "content": "Hello! Introduce yourself."}],
            character_context=character_context,
            lang=user.get("target_lang", "zh"),
            user_id=user["sub"],
            user_plan=user.get("plan", "free"),
            preferred_model=user.get("model_preference"),
        )
    except QuotaExceededError as e:
        return APIResponse(code=2002, message=str(e), data={"session_id": session_id})
    except Exception as e:
        greeting = f"Greetings, traveler. I am {data.character}. (AI unavailable: {e})"

    _sessions[session_id]["messages"].append({"role": "assistant", "content": greeting})
    return APIResponse(data={"session_id": session_id, "greeting": greeting})


@router.post("/message")
async def send_message(data: ChatMessageRequest, user: dict = Depends(get_current_user)):
    session = _sessions.get(data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session["messages"].append({"role": "user", "content": data.message})

    character_context = f"Historical character: {session['character']} from story {session['story_id']}"
    try:
        reply = await model_router.chat(
            messages=session["messages"],
            character_context=character_context,
            lang=user.get("target_lang", "zh"),
            user_id=user["sub"],
            user_plan=user.get("plan", "free"),
            preferred_model=user.get("model_preference"),
        )
    except QuotaExceededError as e:
        return APIResponse(code=2002, message=str(e), data=None)

    session["messages"].append({"role": "assistant", "content": reply})
    return APIResponse(data={"reply": reply, "correction": None})
