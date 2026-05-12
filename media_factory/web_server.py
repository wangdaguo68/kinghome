import io
import json
import sys
import traceback
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from zen_trader.config import load_settings
from zen_trader.crawler import fetch_market_data, crawler_to_markdown
from zen_trader.engine import ZenTraderEngine
from zen_trader.exceptions import ZenTraderError
from zen_trader.generators import GENERATOR_REGISTRY, get_generator
from zen_trader.parser import parse_review
from zen_trader.visual.image_prompt import ImagePromptGenerator
from zen_trader.writer import write_content, write_image_prompt

from core.router import ModeRouter

app = Flask(__name__, template_folder="zen_trader/templates")

API_BASE = "https://api.deepseek.com/anthropic"
MODEL = "deepseek-v4-pro"


def _get_settings(provider=None, model=None, platforms=None):
    cli = {"provider": provider, "model": model, "api_base": API_BASE}
    if platforms:
        cli["platforms"] = platforms
    return load_settings(cli_overrides=cli)


@app.route("/")
def index():
    platforms = [
        {"id": "xiaohongshu", "name": "小红书", "desc": "情绪价值 · 心态治愈 · Emoji体"},
        {"id": "wechat", "name": "公众号", "desc": "深度长文 · 🪷禅意复盘 · 仪式感排版"},
        {"id": "xueqiu", "name": "雪球/东财", "desc": "专业哲学 · 技术指标哲学化 · 高净值"},
        {"id": "shipinhao", "name": "视频号/抖音", "desc": "金句挂件 · 每日禅语 · 视频背景"},
        {"id": "weibo", "name": "微博", "desc": "短小精悍 · 直击痛点 · 话题标签"},
    ]
    modes = [
        {"id": "mixed", "name": "🪷 混合模式", "desc": "技术分析 + 佛学哲学（经典禅交易员）"},
        {"id": "trading", "name": "📊 交易专家", "desc": "纯技术面分析，无哲学/佛学"},
        {"id": "wisdom", "name": "🧘 智慧心灵", "desc": "佛学/斯多葛/心理学，无市场术语"},
    ]
    wisdom_sources = [
        {"id": "daily", "name": "每日自动", "desc": "从语录库随机选一条生成"},
        {"id": "topic", "name": "主题输入", "desc": "输入你想探讨的话题"},
        {"id": "quote", "name": "指定语录", "desc": "从语录库中挑选一条深度解读"},
    ]
    return render_template("index.html", platforms=platforms, modes=modes, wisdom_sources=wisdom_sources)


@app.route("/api/crawl", methods=["POST"])
def api_crawl():
    try:
        data = fetch_market_data()
        md = crawler_to_markdown(data)
        return jsonify({"ok": True, "markdown": md, "date": data.date, "sentiment": data.market_sentiment})
    except ZenTraderError as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/parse", methods=["POST"])
def api_parse():
    body = request.get_json() or {}
    md_text = body.get("markdown", "")
    if not md_text.strip():
        return jsonify({"ok": False, "error": "复盘内容不能为空"}), 400
    try:
        tmp = Path("input/_web_temp.md")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(md_text, encoding="utf-8")
        review = parse_review(tmp)
        return jsonify({
            "ok": True,
            "sentiment": review.trader_sentiment,
            "date": review.date,
            "indices": review.market_indices,
        })
    except ZenTraderError as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def api_generate():
    body = request.get_json() or {}
    md_text = body.get("markdown", "")
    platforms_str = body.get("platforms", "xiaohongshu,wechat,xueqiu,shipinhao,weibo")
    provider = body.get("provider") or "anthropic"
    model = body.get("model") or MODEL
    generate_image = body.get("generate_image", True)
    mode = body.get("mode", "mixed")
    wisdom_source = body.get("wisdom_source", "daily")
    user_topic = body.get("user_topic", "")
    quote_id = body.get("quote_id", "")

    platforms = [p.strip() for p in platforms_str.split(",") if p.strip()]

    if mode in ("trading", "wisdom"):
        return _generate_new_mode(mode, md_text, platforms, wisdom_source, user_topic, quote_id)

    if not md_text.strip():
        return jsonify({"ok": False, "error": "复盘内容不能为空"}), 400

    def generate():
        try:
            settings = _get_settings(provider=provider, model=model, platforms=platforms_str)
            tmp = Path("input/_web_temp.md")
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(md_text, encoding="utf-8")
            review = parse_review(tmp)

            yield f"data: {json.dumps({'type': 'status', 'message': '正在启动 AI 引擎...', 'step': 'init'})}\n\n"

            engine = ZenTraderEngine(settings)

            yield f"data: {json.dumps({'type': 'status', 'message': 'Stage 1: 技术分析中...', 'step': 'stage1'})}\n\n"
            enriched = engine.enrich(review)

            yield f"data: {json.dumps({'type': 'status', 'message': f'分析完成，核心叙事: {enriched.key_narrative[:60]}...', 'step': 'enriched', 'narrative': enriched.key_narrative})}\n\n"

            results = []
            for i, platform in enumerate(platforms):
                if platform not in GENERATOR_REGISTRY:
                    continue
                yield f"data: {json.dumps({'type': 'status', 'message': f'正在生成 {platform} 内容 ({i+1}/{len(platforms)})...', 'step': 'generating', 'platform': platform})}\n\n"
                gen = get_generator(platform, engine)
                content = gen.generate(enriched, sentiment=review.trader_sentiment)
                text_dir = Path(settings.paths.output_dir) / "text"
                filepath = write_content(content, text_dir)
                results.append({
                    "platform": platform,
                    "title": content.title,
                    "body": content.body,
                    "hashtags": content.hashtags,
                    "file": str(filepath),
                })
                yield f"data: {json.dumps({'type': 'platform_done', 'platform': platform, 'title': content.title, 'body': content.body, 'hashtags': content.hashtags, 'file': str(filepath)})}\n\n"

            if generate_image:
                yield f"data: {json.dumps({'type': 'status', 'message': '正在生成封面图提示词...', 'step': 'image'})}\n\n"
                img_gen = ImagePromptGenerator(engine)
                img_prompt = img_gen.generate(enriched, sentiment=review.trader_sentiment)
                img_dir = Path(settings.paths.output_dir) / "image_prompts"
                img_path = write_image_prompt(img_prompt, img_dir)
                yield f"data: {json.dumps({'type': 'image_done', 'midjourney': img_prompt.midjourney_prompt, 'dalle': img_prompt.dalle_prompt, 'description_cn': img_prompt.description_cn, 'file': str(img_path)})}\n\n"

            yield f"data: {json.dumps({'type': 'complete', 'total': len(results)})}\n\n"

        except ZenTraderError as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'{type(e).__name__}: {e}'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _generate_new_mode(mode, md_text, platforms, wisdom_source, user_topic, quote_id):
    try:
        settings = _get_settings(
            provider=request.get_json().get("provider", "anthropic"),
            model=request.get_json().get("model", MODEL),
            platforms=",".join(platforms),
        )
        router = ModeRouter(settings)
        input_data = {
            "raw_text": md_text,
            "platforms": platforms,
            "wisdom_source": wisdom_source,
            "user_text": user_topic,
            "topic": user_topic,
            "quote_id": quote_id,
        }
        results = router.dispatch(mode, input_data)
        return jsonify({"ok": True, "mode": mode, "results": results})
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500


@app.route("/api/quotes", methods=["GET"])
def api_quotes():
    from mode_wisdom.quote_store import QuoteStore
    store = QuoteStore()
    return jsonify({"ok": True, "quotes": store.all})


if __name__ == "__main__":
    print("Zen Trader Web starting...")
    print("   Open: http://127.0.0.1:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
