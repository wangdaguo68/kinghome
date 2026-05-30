from fastapi import APIRouter, Depends, Query
from app.schemas import APIResponse, TTSRequest
from app.middleware.auth import get_current_user
from app.gateway.router import router as model_router

router = APIRouter()


@router.get("/lookup")
async def lookup_word(
    word: str = Query(..., min_length=1),
    lang: str = Query("zh"),
    context: str = Query(""),
    user: dict = Depends(get_current_user),
):
    try:
        result = await model_router.lookup_word(
            word, context, lang, user.get("model_preference")
        )
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(code=3001, message=str(e), data=None)


@router.post("/tts")
async def generate_tts(data: TTSRequest, user: dict = Depends(get_current_user)):
    return APIResponse(
        code=0,
        message="TTS not yet implemented — use edge-tts on client side",
        data={"audio_url": None},
    )


@router.put("/progress")
async def update_progress(user: dict = Depends(get_current_user)):
    return APIResponse(data={"saved": True})
