import json
import random
from pathlib import Path


class QuoteStore:
    def __init__(self, library_path: str = "input/quotes_library.json"):
        self.library_path = Path(library_path)
        self._quotes: list[dict] = []
        self._load()

    def _load(self):
        if self.library_path.exists():
            data = json.loads(self.library_path.read_text(encoding="utf-8"))
            self._quotes = data if isinstance(data, list) else data.get("quotes", [])

    def save(self):
        self.library_path.parent.mkdir(parents=True, exist_ok=True)
        self.library_path.write_text(
            json.dumps(self._quotes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @property
    def all(self) -> list[dict]:
        return list(self._quotes)

    def get(self, quote_id: str) -> dict | None:
        for q in self._quotes:
            if q.get("id") == quote_id:
                return dict(q)
        return None

    def random(self, category: str | None = None) -> dict | None:
        pool = self._quotes
        if category:
            pool = [q for q in pool if q.get("category") == category]
        if not pool:
            return None
        return dict(random.choice(pool))

    def search(self, keyword: str) -> list[dict]:
        kw = keyword.lower()
        results = []
        for q in self._quotes:
            text = json.dumps(q, ensure_ascii=False).lower()
            if kw in text:
                results.append(dict(q))
        return results

    def add(self, quote: dict):
        if "id" not in quote:
            quote["id"] = f"quote_{len(self._quotes) + 1:04d}"
        self._quotes.append(quote)
        self.save()

    def remove(self, quote_id: str) -> bool:
        before = len(self._quotes)
        self._quotes = [q for q in self._quotes if q.get("id") != quote_id]
        if len(self._quotes) < before:
            self.save()
            return True
        return False

    def get_reference_texts(self) -> list[str]:
        texts = []
        for q in self._quotes:
            if q.get("text"):
                texts.append(q["text"])
            if q.get("source"):
                texts.append(q["source"])
        return texts
