import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
BOOK_LIBRARY_DIR = Path("D:/onlinereading")
CACHE_DIR = DATA_DIR / "cache"
CHROMA_DIR = DATA_DIR / "chroma"
DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR / 'app.db'}"
SYNC_DATABASE_URL = f"sqlite:///{DATA_DIR / 'app.db'}"

# Embedding model
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"

# LLM settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")

DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
