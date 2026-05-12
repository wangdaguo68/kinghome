import re
from dataclasses import dataclass, field


@dataclass
class FactCheckResult:
    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class FactChecker:
    """Mode A: 校验 AI 生成的交易文案中的数据是否与原始输入一致"""

    @staticmethod
    def extract_numbers(text: str) -> dict[str, list[str]]:
        return {
            "percent": re.findall(r"[+-]?\d+\.?\d*%", text),
            "index_points": re.findall(r"\d{3,5}\.?\d*(?=\s*点)", text),
            "volume": re.findall(r"\d{3,5}\.?\d*(?=\s*亿)", text),
        }

    @classmethod
    def verify(cls, generated: str, source_data: str) -> FactCheckResult:
        result = FactCheckResult()
        source_nums = cls.extract_numbers(source_data)
        gen_nums = cls.extract_numbers(generated)

        for pct in gen_nums.get("percent", []):
            if pct not in source_nums.get("percent", []):
                result.warnings.append(f"涨跌幅 {pct} 在原始数据中未找到，可能为幻觉")

        for idx in gen_nums.get("index_points", []):
            if idx not in source_nums.get("index_points", []):
                result.warnings.append(f"指数点位 {idx} 在原始数据中未找到，可能为幻觉")

        if result.warnings:
            result.passed = False
        return result


class CitationChecker:
    """Mode B: 校验 AI 生成的哲学文案中的经典引用是否准确"""

    @staticmethod
    def extract_citations(text: str) -> list[dict]:
        citations = []
        for match in re.findall(r"《(.+?)》", text):
            citations.append({"type": "book", "text": match})
        for match in re.findall(r"【(.+?)】", text):
            citations.append({"type": "quote_label", "text": match})
        return citations

    @classmethod
    def verify(cls, generated: str, reference_texts: list[str]) -> FactCheckResult:
        result = FactCheckResult()
        citations = cls.extract_citations(generated)

        if not citations:
            result.warnings.append("未检测到任何经典引用标记，Mode B 内容应包含出处引用")
            return result

        all_refs = " ".join(reference_texts)
        for c in citations:
            if c["type"] == "quote_label":
                if c["text"] not in all_refs:
                    result.warnings.append(f"引用片段 【{c['text'][:30]}...】 不在语录库中")

        if not result.warnings:
            result.passed = True
        return result
