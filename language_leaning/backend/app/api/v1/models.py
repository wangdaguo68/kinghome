from fastapi import APIRouter, Depends
from app.schemas import APIResponse
from app.gateway.router import router as model_router

router = APIRouter()


@router.get("")
async def list_models():
    return APIResponse(data={"models": model_router.get_available_models()})
