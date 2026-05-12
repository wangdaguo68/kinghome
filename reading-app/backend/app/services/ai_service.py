import logging
from ..core.config import OPENAI_API_KEY, OLLAMA_BASE_URL, DEFAULT_LLM_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个基于个人图书馆的AI知识助手。用户拥有上万本电子书籍，涵盖各个领域。

根据用户提供的书籍片段和你的知识，回答用户的问题。

回答原则：
1. 优先使用提供的书籍片段中的知识，标注来源
2. 如果书籍片段中有相关但不够完整的信息，可以结合你的知识补充
3. 答案末尾简要列出参考书籍
4. 如果书籍中没有相关内容，坦率说明，用你的知识回答
5. 保持回答简洁有条理，使用markdown格式
6. 当引用书籍内容时，用【书名】标注来源"""


class AIService:
    def __init__(self):
        self.openai_key = OPENAI_API_KEY
        self.ollama_base = OLLAMA_BASE_URL
        self.default_model = DEFAULT_LLM_MODEL

    async def _get_active_provider(self):
        """Get the active LLM provider from the database."""
        try:
            from ..core.database import async_session
            from sqlalchemy import select
            from ..models.settings import LLMProvider
            async with async_session() as db:
                result = await db.execute(
                    select(LLMProvider).where(LLMProvider.is_active == True)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.debug(f"Could not load provider from DB: {e}")
            return None

    async def _get_config(self, model: str = None):
        """Resolve the actual base_url, api_key, and model to use."""
        # First try DB
        provider = await self._get_active_provider()
        if provider:
            logger.info(f"Using DB provider: {provider.name} ({provider.model_id})")
            return {
                "base_url": provider.base_url,
                "api_key": provider.api_key,
                "model": model or provider.model_id,
            }

        # Fall back to env vars
        if self.openai_key:
            return {
                "base_url": "https://api.openai.com/v1",
                "api_key": self.openai_key,
                "model": model or self.default_model,
            }

        # Fall back to Ollama
        if self.ollama_base:
            model_name = (model or "qwen2.5:7b")
            model_name = model_name.replace("gpt-4o-mini", "qwen2.5:7b").replace("gpt-4o", "qwen2.5:14b")
            return {
                "base_url": f"{self.ollama_base}/v1",
                "api_key": "ollama",
                "model": model_name,
            }

        raise RuntimeError("No LLM configured. Please add a provider in Settings or set env vars.")

    def _build_messages(self, message: str, history: list[dict], context: list[str] = None):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if context:
            context_text = "\n\n---\n\n".join(
                f"参考书籍片段 [{i+1}]:\n{c}" for i, c in enumerate(context)
            )
            messages.append({
                "role": "system",
                "content": f"以下是从用户书籍中检索到的相关片段，请在回答时参考：\n\n{context_text}"
            })
        for h in history[-20:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})
        return messages

    async def chat(self, message: str, history: list[dict], context: list[str] = None,
                   model: str = None) -> str:
        cfg = await self._get_config(model)
        messages = self._build_messages(message, history, context)
        return await self._chat_openai_compatible(messages, cfg)

    async def _chat_openai_compatible(self, messages: list[dict], cfg: dict) -> str:
        import httpx
        url = f"{cfg['base_url']}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if cfg["api_key"] and cfg["api_key"] != "ollama":
            headers["Authorization"] = f"Bearer {cfg['api_key']}"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                headers=headers,
                json={
                    "model": cfg["model"],
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
            )
            data = resp.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            raise RuntimeError(f"LLM error ({resp.status_code}): {data}")

    async def chat_stream(self, message: str, history: list[dict], context: list[str] = None,
                          model: str = None):
        cfg = await self._get_config(model)
        messages = self._build_messages(message, history, context)

        url = f"{cfg['base_url']}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if cfg["api_key"] and cfg["api_key"] != "ollama":
            headers["Authorization"] = f"Bearer {cfg['api_key']}"

        import httpx
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST", url,
                headers=headers,
                json={
                    "model": cfg["model"],
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "stream": True,
                },
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            pass
