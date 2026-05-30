from fastapi import APIRouter, HTTPException, status

from app.schemas import UserCreate, UserLogin, Token, APIResponse
from app.middleware.auth import create_access_token

router = APIRouter()

# In-memory store for dev (replace with DB later)
_users: dict[str, dict] = {}


@router.post("/register", response_model=APIResponse)
async def register(data: UserCreate):
    if data.email in _users:
        raise HTTPException(status_code=400, detail="Email already registered")

    from passlib.hash import bcrypt

    user = {
        "id": f"user_{len(_users)+1}",
        "email": data.email,
        "hashed_password": bcrypt.hash(data.password),
        "nickname": None,
        "native_lang": data.native_lang,
        "target_lang": data.target_lang,
        "model_preference": "claude",
        "plan": "free",
    }
    _users[data.email] = user

    token = create_access_token(user["id"], user["email"])
    return APIResponse(data={"token": token, "user": _to_response(user)})


@router.post("/login", response_model=APIResponse)
async def login(data: UserLogin):
    from passlib.hash import bcrypt

    user = _users.get(data.email)
    if not user or not bcrypt.verify(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Email or password incorrect")

    token = create_access_token(user["id"], user["email"])
    return APIResponse(data={"token": token, "user": _to_response(user)})


def _to_response(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "nickname": user.get("nickname"),
        "native_lang": user["native_lang"],
        "target_lang": user["target_lang"],
        "model_preference": user.get("model_preference", "claude"),
        "plan": user.get("plan", "free"),
    }
