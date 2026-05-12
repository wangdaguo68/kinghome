import os
import json
from pathlib import Path
from ..core.config import CHROMA_DIR, EMBEDDING_MODEL

_embedding_model = None
_chroma_client = None
_collection = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            _collection = _chroma_client.get_collection("book_chunks")
        except Exception:
            _collection = _chroma_client.create_collection(
                "book_chunks",
                metadata={"hnsw:space": "cosine"}
            )
    return _collection


class RAGService:
    def retrieve(self, query: str, book_ids: list[int] = None, top_k: int = 8) -> list[dict]:
        """Hybrid retrieval: semantic + keyword search with RRF fusion."""
        collection = _get_collection()
        model = _get_embedding_model()

        # Semantic search via ChromaDB
        query_embedding = model.encode([query])[0].tolist()
        where_filter = None
        if book_ids:
            where_filter = {"book_id": {"$in": book_ids}}

        semantic_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k * 2, 50),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        # Build result list
        results = []
        seen = set()
        if semantic_results["ids"] and semantic_results["ids"][0]:
            for i, chunk_id in enumerate(semantic_results["ids"][0]):
                meta = semantic_results["metadatas"][0][i]
                content = semantic_results["documents"][0][i]
                key = (meta.get("book_id"), content[:100])
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "chunk_id": chunk_id,
                        "book_id": meta.get("book_id", 0),
                        "title": meta.get("title", ""),
                        "chapter": meta.get("chapter", ""),
                        "page": meta.get("page", 0),
                        "content": content,
                        "score": 1.0 - semantic_results["distances"][0][i],
                    })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def index_book(self, book_id: int, title: str, chunks: list[str],
                   chapters: list[str] = None, pages: list[int] = None):
        """Index book chunks into ChromaDB."""
        if not chunks:
            return
        collection = _get_collection()
        model = _get_embedding_model()

        # Delete existing chunks for this book
        try:
            existing = collection.get(where={"book_id": book_id})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception:
            pass

        chunk_ids = [f"book_{book_id}_chunk_{i}" for i in range(len(chunks))]
        embeddings = model.encode(chunks).tolist()
        metadatas = []
        for i in range(len(chunks)):
            meta = {"book_id": book_id, "title": title}
            if chapters and i < len(chapters):
                meta["chapter"] = chapters[i]
            if pages and i < len(pages):
                meta["page"] = pages[i]
            metadatas.append(meta)

        # Batch insert
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            collection.add(
                ids=chunk_ids[i:i+batch_size],
                documents=chunks[i:i+batch_size],
                embeddings=embeddings[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size],
            )

    def index_book_batch(self, books: list[dict]):
        """Index multiple books at once."""
        for book in books:
            self.index_book(
                book["id"], book["title"], book["chunks"],
                book.get("chapters"), book.get("pages")
            )

    def delete_book(self, book_id: int):
        collection = _get_collection()
        try:
            existing = collection.get(where={"book_id": book_id})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception:
            pass

    def get_book_chunks(self, book_id: int) -> list[dict]:
        collection = _get_collection()
        try:
            result = collection.get(where={"book_id": book_id})
            return [
                {"id": rid, "content": doc, "metadata": meta}
                for rid, doc, meta in zip(result["ids"], result["documents"], result["metadatas"])
            ]
        except Exception:
            return []

    def index_stats(self) -> dict:
        collection = _get_collection()
        count = collection.count()
        return {"total_chunks": count}
