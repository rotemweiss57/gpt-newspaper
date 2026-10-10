"""Print a newspaper from the terminal.

    python -m backend.cli "AI agents" "Space exploration" --layout front --open

Great for a daily cron job. Keys come from the environment (or .env).
"""

import argparse
import asyncio
import sys
import webbrowser
from pathlib import Path

from .agents import NoArticlesError
from .config import LANGUAGES, OUTPUTS_DIR
from .graph import stream_newspaper
from .images import IMAGE_STYLES, PHOTOS
from .setup import SetupError, make_context

LAYOUTS = {"classic": "layout_1", "digest": "layout_2", "front": "layout_3"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m backend.cli", description="Print your personalized AI newspaper.")
    parser.add_argument("topics", nargs="+", help='topics to cover, e.g. "AI agents" "Formula 1"')
    parser.add_argument("--layout", choices=LAYOUTS, default="classic")
    parser.add_argument("--language", choices=LANGUAGES, default="en", metavar="CODE", help="e.g. en, es, he, ja")
    parser.add_argument("--model", help='any LangChain model, e.g. "anthropic:claude-sonnet-5-5" (default: LLM_MODEL)')
    parser.add_argument("--images", choices=[*IMAGE_STYLES, PHOTOS], help="illustration style, or news photos")
    parser.add_argument("--open", action="store_true", help="open the newspaper in your browser when it's ready")
    parser.add_argument("--quiet", action="store_true", help="only print the path of the finished newspaper")
    return parser.parse_args(argv)


async def run(args: argparse.Namespace) -> Path:
    context = make_context(model=args.model, language=args.language, images=args.images, allow_override=True)
    log = (lambda *_: None) if args.quiet else (lambda line: print(line, file=sys.stderr, flush=True))
    log(f"📰  Printing {len(args.topics)} {'story' if len(args.topics) == 1 else 'stories'} with {context.model}\n")

    async for event in stream_newspaper(args.topics, LAYOUTS[args.layout], context):
        if event["type"] == "progress":
            label = f"[{event['topic']}]" if event.get("topic") else "[newsroom]"
            log(f"  {label:<24} {event['message']}")
        elif event["type"] == "done":
            path = OUTPUTS_DIR / event["url"].removeprefix("/outputs/")
            log(
                f"\n✓ {event['articles']} stories on the front page"
                + (f", {event['failed']} failed" if event["failed"] else "")
            )
            return path
    raise RuntimeError("The newsroom stopped before the newspaper was finished")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        path = asyncio.run(run(args))
    except (SetupError, NoArticlesError) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130

    print(path)
    if args.open:
        webbrowser.open(path.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
