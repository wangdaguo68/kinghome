from core.generator import PlatformGenerator, PLATFORM_IDS
from core.provider import get_provider
from core.validator import CitationChecker
from core.writer import write_all_contents
from mode_wisdom.quote_store import QuoteStore
from mode_wisdom.prompts import SYSTEM_PROMPTS, USER_TEMPLATES


class WisdomPipeline:
    def __init__(self, settings):
        self.settings = settings
        self.provider = get_provider(settings)
        self.quote_store = QuoteStore()
        self.checker = CitationChecker()

    def run(self, input_data: dict) -> list[dict]:
        wisdom_source = input_data.get("wisdom_source", "daily")
        platforms = input_data.get("platforms", list(PLATFORM_IDS))
        if isinstance(platforms, str):
            platforms = [p.strip() for p in platforms.split(",") if p.strip()]

        context = self._build_context(wisdom_source, input_data)
        model = self.settings.ai.model

        results = []
        for p_id in platforms:
            if p_id not in SYSTEM_PROMPTS or p_id == "base":
                continue
            gen = PlatformGenerator(
                platform=p_id,
                system_prompt=SYSTEM_PROMPTS[p_id],
                user_template=USER_TEMPLATES[p_id],
                provider=self.provider,
                model=model,
            )
            template_vars = {
                "theme": context["theme"],
                "primary_text": context["primary_text"],
                "source_metadata": context["source_metadata"],
                "approach": context["approach"],
                "tone": context["tone"],
                "user_context": context.get("user_context", ""),
                "additional_quotes": context.get("additional_quotes", ""),
            }
            content = gen.generate(**template_vars)

            check = self.checker.verify(content.body, self.quote_store.get_reference_texts())
            if not check.passed and check.warnings:
                content.body = f"[引用校验警告: {'; '.join(check.warnings)}]\n\n{content.body}"

            results.append({
                "platform": p_id,
                "title": content.title,
                "body": content.body,
                "hashtags": content.hashtags,
            })

        output_dir = f"{self.settings.paths.output_dir}/text"
        write_all_contents(results, output_dir)
        return results

    def _build_context(self, wisdom_source: str, input_data: dict) -> dict:
        if wisdom_source == "topic":
            return self._from_topic(input_data)
        elif wisdom_source == "quote":
            return self._from_quote(input_data)
        else:
            return self._from_daily()

    def _from_topic(self, input_data: dict) -> dict:
        user_text = input_data.get("user_text", "") or input_data.get("topic", "")
        approach = input_data.get("approach", "mixed")
        tone = input_data.get("tone", "gentle")
        return {
            "theme": user_text or "如何面对生活中的无常与变化",
            "primary_text": "",
            "source_metadata": "用户提问",
            "approach": approach,
            "tone": tone,
            "user_context": user_text,
            "additional_quotes": "",
        }

    def _from_quote(self, input_data: dict) -> dict:
        quote_id = input_data.get("quote_id", "")
        quote = self.quote_store.get(quote_id) if quote_id else None
        if not quote:
            quote = self.quote_store.random() or {
                "text": "凡所有相，皆是虚妄。若见诸相非相，则见如来。",
                "source": "金刚经·第五品",
                "category": "buddhism",
                "tags": ["佛法", "空性"],
            }
        related = self.quote_store.search(quote.get("category", ""))
        additional = "\n".join(
            f"- {q.get('text', '')}（{q.get('source', '')}）"
            for q in related[:3] if q.get("id") != quote.get("id")
        )
        return {
            "theme": quote.get("commentary_hint", quote.get("text", "")),
            "primary_text": quote.get("text", ""),
            "source_metadata": quote.get("source", ""),
            "approach": quote.get("category", "mixed"),
            "tone": "academic",
            "user_context": "",
            "additional_quotes": additional,
        }

    def _from_daily(self) -> dict:
        quote = self.quote_store.random()
        if not quote:
            quote = {
                "text": "凡所有相，皆是虚妄。若见诸相非相，则见如来。",
                "source": "金刚经·第五品",
                "category": "buddhism",
                "tags": ["佛法", "空性"],
            }
        return {
            "theme": f"每日智慧：{quote.get('source', '')}",
            "primary_text": quote.get("text", ""),
            "source_metadata": quote.get("source", ""),
            "approach": quote.get("category", "mixed"),
            "tone": "gentle",
            "user_context": "日常反思",
            "additional_quotes": "",
        }
