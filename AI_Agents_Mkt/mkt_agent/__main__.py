"""CLI: python -m mkt_agent "Company name" [website] [-n 3] [--news-days 90] [--review] [--no-cache] [--no-save]"""

import argparse
import asyncio
import sys
import time
from contextlib import aclosing

from . import config
from .orchestrator import make_checkpointer, research_inputs, stream_research
from .report import briefing_markdown
from .storage import save_report


def review_in_terminal(proposal: dict) -> list[dict]:
    """Show the discovered competitors and return the approved list."""
    print("\nDiscovered competitors:", file=sys.stderr)
    for i, c in enumerate(proposal["competitors"], 1):
        print(f"  {i}. {c['name']} ({c['website'] or 'no website'}) - {c['reason']}", file=sys.stderr)
    answer = input(
        "Press Enter to approve, or type a replacement list as 'Name=domain, Name=domain': "
    ).strip()
    if not answer:
        return proposal["competitors"]
    approved = []
    for item in filter(None, (part.strip() for part in answer.split(","))):
        name, _, website = item.partition("=")
        approved.append({"name": name.strip(), "website": website.strip(), "reason": "Added by reviewer"})
    return approved


async def main(args: argparse.Namespace) -> None:
    start = time.perf_counter()
    checkpointer = make_checkpointer()
    inputs = research_inputs(
        args.company, args.website, num_competitors=args.competitors, news_days=args.news_days, review=args.review
    )
    resume = None
    while True:
        events = stream_research(
            inputs if resume is None else None, resume=resume, checkpointer=checkpointer, use_cache=not args.no_cache
        )
        async with aclosing(events):  # close the stream (and Keenable connection) in this task
            async for kind, data in events:
                if kind == "update":
                    for node in data:
                        print(f"[{time.perf_counter() - start:5.1f}s] finished: {node}", file=sys.stderr)
                elif kind == "review":
                    resume = await asyncio.to_thread(review_in_terminal, data)
                else:
                    print(briefing_markdown(data))
                    if not args.no_save:
                        print(f"Saved to {save_report(data)}", file=sys.stderr)
                    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python -m mkt_agent", description="Competitive market research agent")
    parser.add_argument("company")
    parser.add_argument("website", nargs="?", default="")
    parser.add_argument("-n", "--competitors", type=int, default=config.NUM_COMPETITORS,
                        choices=range(1, config.MAX_COMPETITORS + 1), metavar=f"1-{config.MAX_COMPETITORS}")
    parser.add_argument("--news-days", type=int, default=config.NEWS_LOOKBACK_DAYS, help="news lookback window")
    parser.add_argument("--review", action="store_true", help="review the competitors before researching them")
    parser.add_argument("--no-cache", action="store_true", help="force fresh searches and LLM calls")
    parser.add_argument("--no-save", action="store_true", help="don't save the briefing to reports/")
    asyncio.run(main(parser.parse_args()))
