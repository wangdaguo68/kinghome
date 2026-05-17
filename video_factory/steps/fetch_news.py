import os
import requests

from pipeline.context import PipelineContext
from pipeline.base import Step

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class Step(Step):
    def __init__(self, config: dict):
        self.config = config

    def run(self, ctx: PipelineContext) -> None:
        if not BRAVE_API_KEY:
            raise RuntimeError("BRAVE_API_KEY env var not set")

        max_items = self.config.get("max_items", 5)
        select_top = self.config.get("select_top", 3)

        results = self._search(ctx.topic, max_items)
        top = results[:select_top]

        ctx.artifacts["news_items"] = top
        ctx.log(f"fetch: got {len(results)} results, selected top {len(top)}")

    def _search(self, query: str, count: int) -> list[dict]:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": BRAVE_API_KEY,
        }
        resp = requests.get(
            BRAVE_SEARCH_URL,
            params={"q": query, "count": count},
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        items = []
        for r in data.get("web", {}).get("results", []):
            items.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "description": r.get("description", ""),
            })
        return items
