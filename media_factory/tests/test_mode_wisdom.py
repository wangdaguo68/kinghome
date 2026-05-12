import json
import pytest
from pathlib import Path
from mode_wisdom.quote_store import QuoteStore


class TestQuoteStore:
    @pytest.fixture
    def empty_store(self, tmp_path):
        lib = tmp_path / "test_quotes.json"
        lib.write_text("[]", encoding="utf-8")
        return QuoteStore(str(lib))

    @pytest.fixture
    def populated_store(self, tmp_path):
        lib = tmp_path / "test_quotes.json"
        quotes = [
            {
                "id": "test_001",
                "source": "金刚经·第一品",
                "text": "如是我闻。一时佛在舍卫国。",
                "tags": ["佛法", "序分"],
                "category": "buddhism",
            },
            {
                "id": "test_002",
                "source": "沉思录·卷一",
                "text": "每日清晨对自己说：今天我会遇到好管闲事的人...",
                "tags": ["斯多葛", "每日练习"],
                "category": "philosophy",
            },
        ]
        lib.write_text(json.dumps(quotes, ensure_ascii=False), encoding="utf-8")
        return QuoteStore(str(lib))

    def test_load_empty(self, empty_store):
        assert empty_store.all == []

    def test_load_quotes(self, populated_store):
        quotes = populated_store.all
        assert len(quotes) == 2

    def test_get_by_id(self, populated_store):
        q = populated_store.get("test_001")
        assert q is not None
        assert q["source"] == "金刚经·第一品"

    def test_get_nonexistent(self, populated_store):
        assert populated_store.get("nonexistent") is None

    def test_random_returns_quote(self, populated_store):
        q = populated_store.random()
        assert q is not None
        assert "text" in q

    def test_random_by_category(self, populated_store):
        q = populated_store.random(category="buddhism")
        assert q is not None
        assert q["category"] == "buddhism"

    def test_random_empty_category(self, populated_store):
        q = populated_store.random(category="psychology")
        assert q is None

    def test_search_by_keyword(self, populated_store):
        results = populated_store.search("金刚")
        assert len(results) == 1
        assert results[0]["id"] == "test_001"

    def test_add_quote(self, empty_store):
        empty_store.add({"source": "测试", "text": "测试内容"})
        assert len(empty_store.all) == 1
        assert "id" in empty_store.all[0]

    def test_remove_quote(self, populated_store):
        assert populated_store.remove("test_001") is True
        assert len(populated_store.all) == 1
        assert populated_store.remove("nonexistent") is False

    def test_get_reference_texts(self, populated_store):
        refs = populated_store.get_reference_texts()
        assert len(refs) >= 2
