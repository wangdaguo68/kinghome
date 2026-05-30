from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.api.v1 import auth, stories, reader, exercises, chat, user, models


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: init DB, Redis, etc.
    yield
    # shutdown


app = FastAPI(
    title="Cultura API",
    description="Story-driven language & culture learning",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(stories.router, prefix="/api/v1/stories", tags=["Stories"])
app.include_router(reader.router, prefix="/api/v1/reader", tags=["Reader"])
app.include_router(exercises.router, prefix="/api/v1/exercises", tags=["Exercises"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User"])
app.include_router(models.router, prefix="/api/v1/models", tags=["Models"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cultura-api"}
