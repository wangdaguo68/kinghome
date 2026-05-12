import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..core.database import get_db
from ..models.settings import LLMProvider

logger = logging.getLogger(__name__)
router = APIRouter()


class ProviderCreate(BaseModel):
    name: str
    base_url: str
    api_key: str = ""
    model_id: str
    is_active: bool = False


class ProviderUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model_id: str | None = None
    is_active: bool | None = None


class ProviderOut(BaseModel):
    id: int
    name: str
    base_url: str
    api_key: str = ""
    model_id: str
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class TestConnectionRequest(BaseModel):
    base_url: str
    api_key: str
    model_id: str


@router.get("/providers", response_model=list[ProviderOut])
async def list_providers(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(LLMProvider).order_by(LLMProvider.created_at))).scalars().all()
    return [ProviderOut(
        id=r.id, name=r.name, base_url=r.base_url,
        api_key=_mask_key(r.api_key), model_id=r.model_id,
        is_active=r.is_active, created_at=r.created_at.isoformat()
    ) for r in rows]


@router.post("/providers", response_model=ProviderOut)
async def create_provider(data: ProviderCreate, db: AsyncSession = Depends(get_db)):
    if data.is_active:
        await _deactivate_all(db)
    provider = LLMProvider(
        name=data.name,
        base_url=data.base_url.rstrip("/"),
        api_key=data.api_key,
        model_id=data.model_id,
        is_active=data.is_active,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return ProviderOut(
        id=provider.id, name=provider.name, base_url=provider.base_url,
        api_key=_mask_key(provider.api_key), model_id=provider.model_id,
        is_active=provider.is_active, created_at=provider.created_at.isoformat()
    )


@router.put("/providers/{provider_id}", response_model=ProviderOut)
async def update_provider(provider_id: int, data: ProviderUpdate, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Provider not found")
    if data.name is not None:
        p.name = data.name
    if data.base_url is not None:
        p.base_url = data.base_url.rstrip("/")
    if data.api_key is not None:
        p.api_key = data.api_key
    if data.model_id is not None:
        p.model_id = data.model_id
    if data.is_active is not None and data.is_active:
        await _deactivate_all(db)
        p.is_active = True
    elif data.is_active is not None:
        p.is_active = data.is_active
    await db.commit()
    await db.refresh(p)
    return ProviderOut(
        id=p.id, name=p.name, base_url=p.base_url,
        api_key=_mask_key(p.api_key), model_id=p.model_id,
        is_active=p.is_active, created_at=p.created_at.isoformat()
    )


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Provider not found")
    await db.delete(p)
    await db.commit()
    return {"ok": True}


@router.post("/providers/test")
async def test_connection(data: TestConnectionRequest):
    """Test connection to an LLM provider by sending a simple chat request."""
    import httpx
    import time

    base_url = data.base_url.rstrip("/")
    messages = [{"role": "user", "content": "Hi"}]

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {data.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": data.model_id,
                    "messages": messages,
                    "max_tokens": 10,
                },
            )
            elapsed_ms = round((time.time() - start) * 1000)
            if resp.status_code == 200:
                body = resp.json()
                if "choices" in body:
                    return {
                        "success": True,
                        "latency_ms": elapsed_ms,
                        "response": body["choices"][0]["message"]["content"][:100],
                    }
                return {"success": False, "error": f"Unexpected response format", "latency_ms": elapsed_ms}
            else:
                detail = resp.text[:300]
                return {"success": False, "error": f"HTTP {resp.status_code}: {detail}", "latency_ms": elapsed_ms}
    except httpx.ConnectError:
        elapsed_ms = round((time.time() - start) * 1000)
        return {"success": False, "error": f"无法连接到 {base_url}，请检查地址是否正确", "latency_ms": elapsed_ms}
    except httpx.TimeoutException:
        elapsed_ms = round((time.time() - start) * 1000)
        return {"success": False, "error": "连接超时 (30s)", "latency_ms": elapsed_ms}
    except Exception as e:
        elapsed_ms = round((time.time() - start) * 1000)
        return {"success": False, "error": str(e), "latency_ms": elapsed_ms}


@router.get("/providers/active")
async def get_active_provider(db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(LLMProvider).where(LLMProvider.is_active == True))).scalar_one_or_none()
    if not p:
        return None
    return ProviderOut(
        id=p.id, name=p.name, base_url=p.base_url,
        api_key=_mask_key(p.api_key), model_id=p.model_id,
        is_active=p.is_active, created_at=p.created_at.isoformat()
    )


async def _deactivate_all(db: AsyncSession):
    await db.execute(update(LLMProvider).values(is_active=False))


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]
