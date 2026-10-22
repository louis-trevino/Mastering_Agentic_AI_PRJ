"""Agent 2 - Competitor Reporter: gathers fresh web and news data for one competitor.

No LLM here: it runs targeted Keenable searches in parallel and returns a raw
dossier (search results grouped by topic) for the analysis agent.
"""

import asyncio
import logging
from datetime import date, timedelta

from .. import config
from ..keenable import KeenableClient
from ..schemas import Competitor

log = logging.getLogger(__name__)


async def gather_dossier(
    keenable: KeenableClient,
    competitor: Competitor,
    industry: str,
    news_days: int = config.NEWS_LOOKBACK_DAYS,
) -> dict[str, list[dict]]:
    name, site = competitor.name, competitor.website or None
    # Off-site queries name the domain and industry so that e.g. "Coda" (coda.io, docs)
    # isn't confused with Coda Payments (coda.co)
    label = f"{name} ({site}) {industry}" if site else f"{name} {industry}"
    news_since = (date.today() - timedelta(days=news_days)).isoformat()

    topics = {
        "pricing": keenable.search(f"{name} pricing plans and prices", site=site),
        "features": keenable.search(f"{name} product features and capabilities", site=site),
        "positioning": keenable.search(f"{label} review: target customers, strengths and weaknesses"),
        "news": keenable.search(f"{label} news and announcements", published_after=news_since),
    }
    results = await asyncio.gather(*topics.values(), return_exceptions=True)
    # A failed topic search shouldn't sink the whole dossier
    for topic, r in zip(topics, results):
        if isinstance(r, Exception):
            log.warning("%s search for %s failed: %s", topic, name, r)
    return {topic: r if isinstance(r, list) else [] for topic, r in zip(topics, results)}
