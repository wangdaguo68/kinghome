import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .auth import COOKIE_NAME, change_password, create_session, ensure_admin, parse_session, require_user, verify_login
from .config import get_settings
from .db import initialize, snapshot_history
from .services.close_collector import CloseCollector, SHANGHAI


collector = CloseCollector()


async def collection_loop() -> None:
    while True:
        now = datetime.now(SHANGHAI)
        status = collector.current().get("collection_status", {})
        job = status.get("job") or {}
        ready = (now.hour, now.minute) >= (get_settings().close_collection_hour, get_settings().close_collection_minute)
        retry_window = now.hour == 15 and now.minute <= 30
        if now.weekday() < 5 and ready and retry_window and job.get("status") != "published" and int(job.get("free_attempts") or 0) < 3:
            await collector.refresh(allow_tdx=True)
            await asyncio.sleep(600)
        else:
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize()
    ensure_admin()
    task = asyncio.create_task(collection_loop())
    yield
    task.cancel()


app = FastAPI(title="KingModel API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)


@app.get("/api/health")
def health() -> dict:
    settings = get_settings()
    status = collector.current().get("collection_status", {})
    return {
        "status": "ok",
        "mcp_configured": bool(settings.tdx_mcp_url and settings.tdx_mcp_token),
        "tushare_configured": bool(settings.tushare_token),
        "tdx_close_enrichment_enabled": settings.tdx_close_enrichment_enabled,
        "tdx_calls_used": status.get("tdx_calls_used", 0),
        "tdx_daily_limit": status.get("tdx_daily_limit", settings.tdx_daily_call_limit),
    }


@app.post("/api/auth/login")
def login(body: LoginRequest, request: Request, response: Response) -> dict:
    client = request.client.host if request.client else "unknown"
    if not verify_login(body.username, body.password, client):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    response.set_cookie(COOKIE_NAME, create_session(body.username), httponly=True, samesite="strict", max_age=get_settings().session_hours * 3600)
    return {"username": body.username}


@app.post("/api/auth/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@app.get("/api/auth/me")
def me(username: Annotated[str, Depends(require_user)]) -> dict:
    return {"username": username}


@app.post("/api/auth/password")
def update_password(body: PasswordChangeRequest, username: Annotated[str, Depends(require_user)]) -> dict:
    if not change_password(username, body.current_password, body.new_password):
        raise HTTPException(status_code=400, detail="当前密码错误")
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard(_: Annotated[str, Depends(require_user)]) -> dict:
    return collector.current()


@app.post("/api/refresh")
async def refresh(_: Annotated[str, Depends(require_user)]) -> dict:
    return await collector.refresh(allow_tdx=False)


@app.get("/api/history")
def history(_: Annotated[str, Depends(require_user)]) -> dict:
    return {"items": snapshot_history()}


@app.get("/api/sentiment")
def sentiment(_: Annotated[str, Depends(require_user)]) -> dict:
    current = collector.current()
    return {"items": current.get("sentiment", []), "policy": "舆情只用于催化、共识和拥挤提示，不直接修改交易评分。"}


@app.websocket("/api/ws")
async def websocket_dashboard(websocket: WebSocket, km_session: Annotated[str | None, Cookie()] = None) -> None:
    if not km_session or not parse_session(km_session):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(collector.current())
            await asyncio.sleep(15)
    except WebSocketDisconnect:
        return
