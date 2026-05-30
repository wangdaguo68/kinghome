from fastapi import APIRouter, Depends
from app.schemas import APIResponse, ExerciseGenerateRequest
from app.middleware.auth import get_current_user
from app.gateway.router import router as model_router
from app.gateway.router import QuotaExceededError

router = APIRouter()


@router.post("/generate")
async def generate_exercises(data: ExerciseGenerateRequest, user: dict = Depends(get_current_user)):
    try:
        exercises = await model_router.generate_exercises(
            story_context=f"Story {data.story_id}, chapter {data.chapter_index}",
            exercise_type=data.exercise_type,
            lang=user.get("target_lang", "zh"),
            user_id=user["sub"],
            user_plan=user.get("plan", "free"),
            preferred_model=user.get("model_preference"),
        )
        return APIResponse(data={"exercises": exercises})
    except QuotaExceededError as e:
        return APIResponse(code=2001, message=str(e), data=None)
    except Exception as e:
        return APIResponse(code=3001, message=str(e), data=None)
