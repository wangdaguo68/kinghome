from pydantic import BaseModel, Field


class AnonymousRegisterRequest(BaseModel):
    user_id: str = Field(min_length=1)


class AnonymousRegisterResponse(BaseModel):
    user_id: str
    recovery_code: str
    quota_remaining: int


class ChatRequest(BaseModel):
    record_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    mood_label: str = Field(min_length=1)
    message: str = Field(min_length=1)
    reply_mode: str = "comfort"


class ChatResponse(BaseModel):
    reply: str
    safety_triggered: bool = False
    fallback: bool = False
    quota_exceeded: bool = False
    quota_remaining: int | None = None


class SummaryRequest(BaseModel):
    record_id: str = Field(min_length=1)
    conversation_text: str = Field(min_length=1)


class SummaryResponse(BaseModel):
    keywords: list[str]
    emotion_color: str
    intensity: str
    summary: str
    comfort_sentence: str
    surface_emotion: str = ""
    real_pain_point: str = ""
    hidden_need: str = ""
    small_action: str = ""
    self_comfort_sentence: str = ""
    fallback: bool = False


class ResonanceNoteCreateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    mood_label: str = Field(min_length=1, max_length=20)
    content: str = Field(min_length=2, max_length=240)


class ResonanceNoteResponse(BaseModel):
    id: str
    mood_label: str
    content: str
    created_at: str
    reactions: dict[str, int] = {}


class ResonanceNoteCreateResponse(BaseModel):
    note: ResonanceNoteResponse | None = None
    safety_triggered: bool = False
    message: str


class ResonanceReactionRequest(BaseModel):
    user_id: str = Field(min_length=1)
    reaction: str = Field(min_length=1, max_length=20)


class ResonanceReactionResponse(BaseModel):
    note_id: str
    reactions: dict[str, int]
