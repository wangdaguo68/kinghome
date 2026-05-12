"""
本地记忆库：ChromaDB 向量存储。
支持两种 Embedding 来源：
  - local  : ChromaDB 自带 ONNX 模型（首次运行自动下载，约 23 MB）
  - api    : OpenAI 兼容接口（openai / 自定义端点）
"""

import json
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from core.database import get_settings

DATA_DIR = Path.home() / ".thinkvault"
CHROMA_DIR = DATA_DIR / "chroma"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

_client: Optional[chromadb.PersistentClient] = None
_collection = None


def _get_embedding_function():
    cfg = get_settings()
    provider = cfg.get("embedding_provider", "local")

    if provider == "api":
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
        return OpenAIEmbeddingFunction(
            api_key=cfg.get("embedding_api_key", ""),
            api_base=cfg.get("embedding_base_url", "https://api.openai.com/v1"),
            model_name=cfg.get("embedding_model", "text-embedding-3-small"),
        )
    else:
        # 本地 ONNX 模型（all-MiniLM-L6-v2，首次自动下载）
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
        return ONNXMiniLM_L6_V2()


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name="memories",
            embedding_function=_get_embedding_function(),
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def reload_collection():
    """修改嵌入配置后调用，重新初始化 collection。"""
    global _client, _collection
    _client = None
    _collection = None


def add_memory(doc_id: str, text: str, metadata: dict):
    """存入一条记忆（消息或摘要）。"""
    col = get_collection()
    col.upsert(
        ids=[doc_id],
        documents=[text],
        metadatas=[metadata],
    )


def search_memory(query: str, top_k: int = 3, where: dict | None = None) -> list[dict]:
    """语义搜索，返回最相关的记忆列表。"""
    col = get_collection()
    count = col.count()
    if count == 0:
        return []
    k = min(top_k, count)
    kwargs = {"query_texts": [query], "n_results": k, "include": ["documents", "metadatas", "distances"]}
    if where:
        kwargs["where"] = where
    results = col.query(**kwargs)

    out = []
    if not results["ids"] or not results["ids"][0]:
        return out
    for i, doc_id in enumerate(results["ids"][0]):
        out.append({
            "id":       doc_id,
            "text":     results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return out


def delete_memory(doc_id: str):
    col = get_collection()
    col.delete(ids=[doc_id])


def delete_topic_memories(topic_id: int):
    """删除某话题的全部记忆。"""
    col = get_collection()
    col.delete(where={"topic_id": str(topic_id)})


def memory_count() -> int:
    return get_collection().count()
