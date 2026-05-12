import argparse
import logging
import sys
import time
from pathlib import Path

from zen_trader.config import load_settings
from zen_trader.crawler import fetch_market_data, save_crawler_output
from zen_trader.engine import ZenTraderEngine
from zen_trader.exceptions import ZenTraderError
from zen_trader.generators import GENERATOR_REGISTRY, get_generator
from zen_trader.parser import parse_review
from zen_trader.visual.image_prompt import ImagePromptGenerator
from zen_trader.writer import write_all, write_image_prompt


def setup_logging(level: str = "INFO", log_file: str | None = None):
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


def cmd_generate(args):
    cli_overrides = {
        "provider": args.provider,
        "model": args.model,
        "api_base": args.api_base,
    }
    if args.platforms and args.platforms != "all":
        cli_overrides["platforms"] = args.platforms
    settings = load_settings(cli_overrides=cli_overrides)
    setup_logging(settings.logging.level, settings.logging.file)
    logger = logging.getLogger(__name__)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    logger.info("Parsing review: %s", input_path)
    review = parse_review(input_path)
    logger.info("Market sentiment: %s", review.trader_sentiment)

    logger.info("Initializing AI engine (provider=%s, model=%s)", settings.ai.provider, settings.ai.model)
    engine = ZenTraderEngine(settings)

    logger.info("Stage 1+2: Enriching content via AI...")
    t0 = time.time()
    enriched = engine.enrich(review)
    logger.info("Enrichment complete (%.1fs). Key narrative: %s", time.time() - t0, enriched.key_narrative[:80])

    platforms = settings.platforms.enabled
    if args.platforms and args.platforms != "all":
        platforms = [p.strip() for p in args.platforms.split(",")]

    contents = []
    for platform in platforms:
        if platform not in GENERATOR_REGISTRY:
            logger.warning("Unknown platform '%s', skipping", platform)
            continue
        logger.info("Generating %s content...", platform)
        gen = get_generator(platform, engine)
        content = gen.generate(enriched, sentiment=review.trader_sentiment)
        contents.append(content)
        logger.info("  %s: %s...", platform, content.title[:50] if content.title else "(no title)")

    text_dir = Path(settings.paths.output_dir) / "text"
    paths = write_all(contents, text_dir)
    for p in paths:
        logger.info("Written: %s", p)

    if not args.image_only and args.image_only is not False:
        pass

    logger.info("Generating cover image prompts...")
    img_gen = ImagePromptGenerator(engine)
    img_prompt = img_gen.generate(
        enriched,
        sentiment=review.trader_sentiment,
        style=settings.image.default_style,
        aspect_ratio=settings.image.aspect_ratio,
    )
    img_dir = Path(settings.paths.output_dir) / "image_prompts"
    img_path = write_image_prompt(img_prompt, img_dir)
    logger.info("Cover image prompt: %s", img_path)

    elapsed = time.time() - t0
    logger.info("All done! %d platforms + cover image generated in %.1fs", len(contents), elapsed)


def cmd_image_only(args):
    settings = load_settings(
        cli_overrides={
            "provider": args.provider,
            "model": args.model,
            "api_base": args.api_base,
        }
    )
    setup_logging(settings.logging.level, settings.logging.file)
    logger = logging.getLogger(__name__)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    review = parse_review(input_path)
    engine = ZenTraderEngine(settings)
    enriched = engine.enrich(review)

    img_gen = ImagePromptGenerator(engine)
    img_prompt = img_gen.generate(
        enriched,
        sentiment=review.trader_sentiment,
        style=settings.image.default_style,
        aspect_ratio=settings.image.aspect_ratio,
    )
    img_dir = Path(settings.paths.output_dir) / "image_prompts"
    img_path = write_image_prompt(img_prompt, img_dir)
    logger.info("Cover image prompt: %s", img_path)


def cmd_crawl(args):
    settings = load_settings()
    setup_logging(settings.logging.level, settings.logging.file)
    logger = logging.getLogger(__name__)

    logger.info("Fetching A-share market data...")
    data = fetch_market_data()
    logger.info("Market sentiment: %s, limit up: %d, limit down: %d",
                data.market_sentiment, data.limit_up_count, data.limit_down_count)

    input_dir = Path(settings.paths.input_dir)
    filepath = save_crawler_output(data, input_dir)
    logger.info("Saved to: %s", filepath)


def cmd_crawl_and_generate(args):
    cli_overrides = {
        "provider": args.provider,
        "model": args.model,
        "api_base": args.api_base,
    }
    if args.platforms and args.platforms != "all":
        cli_overrides["platforms"] = args.platforms
    settings = load_settings(cli_overrides=cli_overrides)
    setup_logging(settings.logging.level, settings.logging.file)
    logger = logging.getLogger(__name__)

    logger.info("Step 1: Crawling market data...")
    data = fetch_market_data()
    input_dir = Path(settings.paths.input_dir)
    crawl_path = save_crawler_output(data, input_dir)
    logger.info("Crawler output: %s", crawl_path)

    logger.info("Step 2: Parsing and generating...")
    review = parse_review(crawl_path)
    engine = ZenTraderEngine(settings)

    enriched = engine.enrich(review)

    platforms = settings.platforms.enabled
    if args.platforms and args.platforms != "all":
        platforms = [p.strip() for p in args.platforms.split(",")]

    contents = []
    for platform in platforms:
        if platform not in GENERATOR_REGISTRY:
            logger.warning("Unknown platform '%s', skipping", platform)
            continue
        gen = get_generator(platform, engine)
        content = gen.generate(enriched, sentiment=review.trader_sentiment)
        contents.append(content)

    text_dir = Path(settings.paths.output_dir) / "text"
    paths = write_all(contents, text_dir)
    for p in paths:
        logger.info("Written: %s", p)

    img_gen = ImagePromptGenerator(engine)
    img_prompt = img_gen.generate(enriched, sentiment=review.trader_sentiment)
    img_dir = Path(settings.paths.output_dir) / "image_prompts"
    img_path = write_image_prompt(img_prompt, img_dir)
    logger.info("Cover image prompt: %s", img_path)


def main():
    parser = argparse.ArgumentParser(
        prog="zen-trader",
        description="Zen Trader (禅意交易员) — A-share content generation with Buddhist wisdom",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # generate
    gen = subparsers.add_parser("generate", help="Generate content from Markdown review notes")
    gen.add_argument("--input", "-i", required=True, help="Path to Markdown review file")
    gen.add_argument("--platforms", "-p", default="all",
                     help="Comma-separated platforms: xiaohongshu,wechat,xueqiu,shipinhao,weibo")
    gen.add_argument("--provider", default=None, help="AI provider override")
    gen.add_argument("--model", "-m", default=None, help="AI model override")
    gen.add_argument("--api-base", default=None, help="Custom API base URL")
    gen.add_argument("--image-only", action="store_true", help="Only generate cover image prompts")
    gen.set_defaults(func=cmd_generate)

    # crawl
    crawl = subparsers.add_parser("crawl", help="Fetch A-share market sentiment data")
    crawl.set_defaults(func=cmd_crawl)

    # crawl-and-generate
    cg = subparsers.add_parser("crawl-and-generate", help="Crawl data then generate all content")
    cg.add_argument("--platforms", "-p", default="all",
                    help="Comma-separated platforms")
    cg.add_argument("--provider", default=None, help="AI provider override")
    cg.add_argument("--model", "-m", default=None, help="AI model override")
    cg.add_argument("--api-base", default=None, help="Custom API base URL")
    cg.set_defaults(func=cmd_crawl_and_generate)

    # image-only
    img = subparsers.add_parser("image-only", help="Only generate cover image prompts")
    img.add_argument("--input", "-i", required=True, help="Path to Markdown review file")
    img.add_argument("--provider", default=None, help="AI provider override")
    img.add_argument("--model", "-m", default=None, help="AI model override")
    img.add_argument("--api-base", default=None, help="Custom API base URL")
    img.set_defaults(func=cmd_image_only)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    try:
        args.func(args)
    except ZenTraderError as e:
        logging.error("%s: %s", type(e).__name__, e)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
