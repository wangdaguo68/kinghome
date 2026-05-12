from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_db
from ..models.book import Book
from ..models.chat import Conversation, Message
from ..schemas import ChatRequest, ChatResponse, ConversationOut, MessageOut
from ..services.ai_service import AIService
from ..services.rag_service import RAGService
import json

router = APIRouter()
ai_service = AIService()
rag_service = RAGService()


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc())
    )).scalars().all()
    return [ConversationOut.model_validate(r) for r in rows]


@router.post("/conversations", response_model=ConversationOut)
async def create_conversation(title: str = "", model: str = "", db: AsyncSession = Depends(get_db)):
    conv = Conversation(title=title or "New Chat", model=model or "")
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ConversationOut.model_validate(conv)


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: int, db: AsyncSession = Depends(get_db)):
    conv = (await db.execute(select(Conversation).where(Conversation.id == conv_id))).scalar_one_or_none()
    if conv:
        await db.delete(conv)
        await db.commit()
    return {"ok": True}


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageOut])
async def get_messages(conv_id: int, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
    )).scalars().all()
    results = []
    for r in rows:
        citations = None
        if r.citations:
            try:
                citations = json.loads(r.citations) if isinstance(r.citations, str) else r.citations
            except Exception:
                pass
        results.append(MessageOut(
            id=r.id, conversation_id=r.conversation_id, role=r.role,
            content=r.content, citations=citations, created_at=r.created_at
        ))
    return results


@router.post("/send", response_model=ChatResponse)
async def send_message(data: ChatRequest, db: AsyncSession = Depends(get_db)):
    conv_id = data.conversation_id
    if not conv_id:
        conv = Conversation(title=data.message[:50], model=data.model)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        conv_id = conv.id

    # Get conversation history
    history_rows = (await db.execute(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
    )).scalars().all()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    # Save user message
    user_msg = Message(conversation_id=conv_id, role="user", content=data.message)
    db.add(user_msg)
    await db.commit()

    # RAG retrieval
    context_chunks = []
    citations = []
    if data.use_rag:
        try:
            retrieved = rag_service.retrieve(data.message, book_ids=data.book_ids, top_k=8)
            context_chunks = [r["content"] for r in retrieved]
            citations = [{"title": r["title"], "book_id": r["book_id"], "chapter": r.get("chapter", ""),
                          "page": r.get("page", 0), "snippet": r["content"][:200]} for r in retrieved]
        except Exception:
            pass

    # Generate response
    try:
        answer = await ai_service.chat(
            message=data.message,
            history=history,
            context=context_chunks,
            model=data.model,
        )
    except Exception as e:
        answer = f"AI service error: {str(e)}. Please check your LLM configuration."

    # Save assistant message
    citations_json = json.dumps(citations, ensure_ascii=False) if citations else None
    assistant_msg = Message(
        conversation_id=conv_id, role="assistant", content=answer, citations=citations_json
    )
    db.add(assistant_msg)

    # Update conversation title if first exchange
    if len(history_rows) == 0:
        conv = (await db.execute(select(Conversation).where(Conversation.id == conv_id))).scalar_one()
        conv.title = data.message[:50]
    await db.commit()

    return ChatResponse(conversation_id=conv_id, message=answer, citations=citations)


@router.post("/stream")
async def stream_message(data: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Streaming chat response."""
    from fastapi.responses import StreamingResponse
    import asyncio

    conv_id = data.conversation_id
    if not conv_id:
        conv = Conversation(title=data.message[:50], model=data.model)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        conv_id = conv.id

    history_rows = (await db.execute(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
    )).scalars().all()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    user_msg = Message(conversation_id=conv_id, role="user", content=data.message)
    db.add(user_msg)
    await db.commit()

    context_chunks = []
    citations = []
    if data.use_rag:
        try:
            retrieved = rag_service.retrieve(data.message, book_ids=data.book_ids, top_k=8)
            context_chunks = [r["content"] for r in retrieved]
            citations = [{"title": r["title"], "book_id": r["book_id"], "chapter": r.get("chapter", ""),
                          "page": r.get("page", 0), "snippet": r["content"][:200]} for r in retrieved]
        except Exception:
            pass

    async def generate():
        full_response = ""
        try:
            async for chunk in ai_service.chat_stream(
                message=data.message,
                history=history,
                context=context_chunks,
                model=data.model,
            ):
                full_response += chunk
                yield f"data: {json.dumps({'chunk': chunk, 'conv_id': conv_id})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        # Save full message
        citations_json = json.dumps(citations, ensure_ascii=False) if citations else None
        assistant_msg = Message(
            conversation_id=conv_id, role="assistant", content=full_response, citations=citations_json
        )
        db.add(assistant_msg)
        if len(history_rows) == 0:
            conv = (await db.execute(select(Conversation).where(Conversation.id == conv_id))).scalar_one()
            conv.title = data.message[:50]
        await db.commit()
        yield f"data: {json.dumps({'done': True, 'conv_id': conv_id, 'citations': citations})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
