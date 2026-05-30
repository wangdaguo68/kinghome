from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    native_lang: str = Field(..., pattern="^(zh|en)$")
    target_lang: str = Field(..., pattern="^(zh|en)$")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    nickname: str | None = None
    native_lang: str
    target_lang: str
    model_preference: str = "claude"
    plan: str = "free"

    class Config:
        from_attributes = True


class APIResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: dict | list | None = None


class PaginatedResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: dict


class StorySummary(BaseModel):
    id: str
    title: str
    title_en: str | None = None
    era: str
    region: str
    cefr_level: str
    summary: str | None = None
    chapter_count: int
    cover_emoji: str | None = None
    tags: list[str] = []


class ChapterContent(BaseModel):
    id: str
    number: int
    title: str
    content_original: str
    content_translation: str | None = None
    vocabulary: list[dict] = []
    cultural_notes: list[dict] = []


class LookupResult(BaseModel):
    word: str
    phonetic: str | None = None
    meaning: str
    example: str | None = None
    etymology: str | None = None


class TTSRequest(BaseModel):
    text: str
    lang: str = "zh"
    speed: float = 1.0


class ExerciseGenerateRequest(BaseModel):
    story_id: str
    chapter_index: int = 0
    exercise_type: str = "vocabulary"


class ChatStartRequest(BaseModel):
    story_id: str
    character: str


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str


class ModelPreferenceUpdate(BaseModel):
    model: str = Field(..., pattern="^(claude|deepseek|qwen|kimi|minimax)$")
