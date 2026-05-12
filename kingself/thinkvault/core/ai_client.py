"""
AI 客户端：数字分身模式。
AI 学习用户记录的所有思维、经历、经验，对话时以用户的思维方式回答。
支持任意 OpenAI 兼容接口（OpenAI / DeepSeek / Ollama / 自定义端点）。
"""

from __future__ import annotations

from typing import Generator

from openai import OpenAI, APIError, APIConnectionError, AuthenticationError

from core.database import get_settings

_client: OpenAI | None = None
_last_cfg_hash: str = ""

# 数字分身核心 system prompt
_TWIN_SYSTEM_PROMPT = """你是用户的数字分身。

你的核心任务：
- 你已经学习了用户记录的所有思维、经历、观点和经验
- 对话时，你要以用户的思维方式、价值观和语言风格来回答
- 优先从用户的记忆中寻找相关内容，引用用户自己的经历和观点
- 当用户问到某个话题时，先思考"用户在这方面有什么积累？"
- 帮助用户发现自己思维中的规律，建立知识之间的连接
- 如果用户问的内容你没有相关记忆，诚实说明，并引导用户补充这方面的内容

行为准则：
- 不要表现得像一个通用 AI 助手，你是用户的思维镜像
- 回答要简洁有力，符合用户的风格（根据其记录推断）
- 主动建立不同记忆之间的联系，帮助用户看到全局
- 遇到用户记录中有矛盾或值得反思的地方，可以温和指出"""


def _get_client() -> OpenAI:
    global _client, _last_cfg_hash
    cfg = get_settings()
    cfg_hash = f"{cfg.get('ai_base_url')}|{cfg.get('ai_api_key')}|{cfg.get('ai_model')}"
    if _client is None or cfg_hash != _last_cfg_hash:
        _client = OpenAI(
            api_key=cfg.get("ai_api_key") or "sk-placeholder",
            base_url=cfg.get("ai_base_url", "https://api.openai.com/v1"),
        )
        _last_cfg_hash = cfg_hash
    return _client


def _get_client_with(base_url: str, api_key: str) -> OpenAI:
    """用指定参数临时创建客户端（用于设置测试）。"""
    return OpenAI(
        api_key=api_key or "sk-placeholder",
        base_url=base_url,
    )


def _build_memory_context(query: str, top_k: int) -> str:
    """检索用户记忆，构建上下文。"""
    try:
        from core.memory import search_memory
        hits = search_memory(query, top_k=top_k)
    except Exception:
        return ""
    if not hits:
        return ""

    lines = ["【用户的相关记忆与经验】"]
    for h in hits:
        meta = h["metadata"]
        role = meta.get("role", "")
        topic = meta.get("topic_name", "")
        date = meta.get("date", "")
        cat = meta.get("category", "")

        prefix = ""
        if role == "note":
            prefix = f"[笔记/{cat}]"
        elif role == "user":
            prefix = f"[对话·我说·{topic}]"
        elif role == "assistant":
            prefix = f"[对话·AI分析·{topic}]"
        elif role == "insight":
            prefix = f"[洞察·{topic}]"
        elif role == "report":
            prefix = "[学习报告]"

        lines.append(f"• {prefix} {date}  {h['text'][:400]}")
    lines.append("【记忆结束】\n")
    return "\n".join(lines)


def chat_stream(
    messages: list[dict],
    user_input: str,
) -> Generator[str, None, None]:
    """
    流式对话（数字分身模式）。
    Yields: str token
    Raises: RuntimeError on API error
    """
    cfg = get_settings()
    client = _get_client()
    model = cfg.get("ai_model", "gpt-4o-mini")
    custom_prompt = cfg.get("ai_system_prompt", "").strip()
    rag_enabled = cfg.get("rag_enabled", "true") == "true"
    top_k = int(cfg.get("rag_top_k", "10"))
    stream_enabled = cfg.get("stream_enabled", "true") == "true"

    base_system = custom_prompt if custom_prompt else _TWIN_SYSTEM_PROMPT

    memory_ctx = ""
    if rag_enabled and user_input:
        memory_ctx = _build_memory_context(user_input, top_k)

    full_system = base_system
    if memory_ctx:
        full_system = f"{base_system}\n\n{memory_ctx}"

    payload = [{"role": "system", "content": full_system}] + messages

    try:
        if stream_enabled:
            response = client.chat.completions.create(
                model=model,
                messages=payload,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        else:
            response = client.chat.completions.create(
                model=model,
                messages=payload,
                stream=False,
            )
            yield response.choices[0].message.content or ""

    except AuthenticationError:
        raise RuntimeError("API Key 无效，请在设置中检查。")
    except APIConnectionError:
        raise RuntimeError("无法连接到 AI 服务，请检查网络或 API 地址。")
    except APIError as e:
        raise RuntimeError(f"API 错误：{e}")


def test_connection(base_url: str, api_key: str, model: str) -> str:
    """测试连接，使用传入的参数（不读数据库）。返回 AI 回复或抛出异常。"""
    client = _get_client_with(base_url, api_key)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "请只回复数字1"}],
            stream=False,
            max_tokens=10,
        )
        return response.choices[0].message.content or "OK"
    except AuthenticationError:
        raise RuntimeError("API Key 无效")
    except APIConnectionError:
        raise RuntimeError("无法连接，请检查 Base URL 和网络")
    except APIError as e:
        raise RuntimeError(f"API 错误：{e}")


def generate_insight(topic_name: str, history_text: str) -> str:
    cfg = get_settings()
    client = _get_client()
    model = cfg.get("ai_model", "gpt-4o-mini")
    prompt = f"""请对话题「{topic_name}」的思考记录进行分析，输出：
1. 核心观点总结（3-5 条）
2. 发现的思维模式或规律
3. 值得深入探索的方向

---
{history_text[:4000]}
---
请用中文回答，结构清晰。"""
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个帮助用户分析思维模式的AI助手。"},
                {"role": "user", "content": prompt},
            ],
        )
        return r.choices[0].message.content or ""
    except Exception as e:
        raise RuntimeError(str(e))


def generate_weekly_report(all_text: str) -> str:
    cfg = get_settings()
    client = _get_client()
    model = cfg.get("ai_model", "gpt-4o-mini")
    prompt = f"""请对以下近期思考记录生成一份学习洞察报告，包含：
1. 本期核心关注主题
2. 重复出现的思维模式
3. 知识连接点（不同话题间的关联）
4. 建议深化的方向

---
{all_text[:6000]}
---
请用中文输出，格式清晰。"""
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个帮助分析思维规律的AI助手。"},
                {"role": "user", "content": prompt},
            ],
        )
        return r.choices[0].message.content or ""
    except Exception as e:
        raise RuntimeError(str(e))
