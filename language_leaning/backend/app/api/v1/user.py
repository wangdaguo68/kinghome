from fastapi import APIRouter, Depends, HTTPException

from app.schemas import APIResponse, ModelPreferenceUpdate
from app.middleware.auth import get_current_user
from app.gateway.router import router as model_router

router = APIRouter()


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    return APIResponse(data={
        "id": user["sub"],
        "email": user.get("email"),
        "plan": user.get("plan", "free"),
        "model_preference": user.get("model_preference", "claude"),
    })


@router.get("/vocabulary")
async def get_vocabulary(page: int = 1, page_size: int = 20, user: dict = Depends(get_current_user)):
    return APIResponse(data={"items": [], "total": 0})


@router.get("/achievements")
async def get_achievements(user: dict = Depends(get_current_user)):
    return APIResponse(data={"achievements": [], "unlocked": 0, "total": 24})


@router.put("/model-preference")
async def update_model_preference(data: ModelPreferenceUpdate, user: dict = Depends(get_current_user)):
    user["model_preference"] = data.model
    return APIResponse(data={"model": data.model})


@router.get("/subscription")
async def get_subscription(user: dict = Depends(get_current_user)):
    plans = {
        "free": {"name": "Free", "price": 0, "daily_stories": 3, "daily_chat": 10},
        "monthly": {"name": "Pro Monthly", "price": 98, "daily_stories": "unlimited", "daily_chat": 200},
        "yearly": {"name": "Pro Yearly", "price": 998, "daily_stories": "unlimited", "daily_chat": 500},
    }
    current = plans.get(user.get("plan", "free"), plans["free"])
    return APIResponse(data={"current_plan": user.get("plan", "free"), "plans": plans, "details": current})


@router.get("/models")
async def list_models(user: dict = Depends(get_current_user)):
    return APIResponse(data={
        "available": model_router.get_available_models(),
        "current": user.get("model_preference", "claude"),
    })
