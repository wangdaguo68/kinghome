import pytest
from core.validator import FactChecker, CitationChecker, FactCheckResult


class TestFactChecker:
    def test_extract_numbers(self):
        text = "上证 3300.50 +0.83%，成交9877亿"
        nums = FactChecker.extract_numbers(text)
        assert "+0.83%" in nums["percent"]
        assert nums["index_points"] or nums["volume"]

    def test_verify_no_warnings_for_matching_data(self):
        source = "上证 +0.83% 深证 +1.21%"
        generated = "今日上证涨了+0.83%，表现不错"
        result = FactChecker.verify(generated, source)
        assert result.passed

    def test_verify_warnings_for_mismatched_data(self):
        source = "上证 +0.83%"
        generated = "今日上证涨了+5.00%"
        result = FactChecker.verify(generated, source)
        assert not result.passed
        assert len(result.warnings) > 0

    def test_fact_check_result_defaults(self):
        r = FactCheckResult()
        assert r.passed is True
        assert r.errors == []
        assert r.warnings == []


class TestCitationChecker:
    def test_extract_citations_from_book_titles(self):
        text = "《金刚经》中说「凡所有相，皆是虚妄」"
        citations = CitationChecker.extract_citations(text)
        assert any(c["type"] == "book" and "金刚经" in c["text"] for c in citations)

    def test_verify_no_citations(self):
        result = CitationChecker.verify("这是一段没有引用的文本", [])
        assert len(result.warnings) > 0

    def test_verify_with_valid_references(self):
        refs = ["凡所有相，皆是虚妄。若见诸相非相，则见如来。", "金刚经·第五品"]
        generated = "《金刚经》告诉我们一个深刻的道理。"
        result = CitationChecker.verify(generated, refs)
        assert result.passed
