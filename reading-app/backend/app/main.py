from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .core.config import DATA_DIR, CACHE_DIR
from .core.database import init_db
from .api import books, reader, highlights, shelf, chat, search, scan, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Reading App", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/cache", StaticFiles(directory=str(CACHE_DIR)), name="cache")
app.mount("/static/data", StaticFiles(directory=str(DATA_DIR)), name="data")

app.include_router(books.router, prefix="/api/books", tags=["books"])
app.include_router(reader.router, prefix="/api/reader", tags=["reader"])
app.include_router(highlights.router, prefix="/api/highlights", tags=["highlights"])
app.include_router(shelf.router, prefix="/api/shelf", tags=["shelf"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(scan.router, prefix="/api/scan", tags=["scan"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
