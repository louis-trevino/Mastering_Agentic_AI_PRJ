"""Agent 1 - Competitor Discovery: finds the company's top direct competitors."""

import asyncio

from .. import config
from ..keenable import KeenableClient, format_results
from ..llm import structured_llm
from ..schemas import CompanyProfile, Competitor, CompetitorList

PROMPT = """You are a competitive intelligence analyst.

Target company:
- Name: {name}
- Website: {website}
- Industry: {industry}
- Description: {description}
- Main products: {products}

Using the search results below (and your general knowledge only to break ties),
identify the top {n} DIRECT competitors of {name}: companies selling a comparable
product to the same customers. Exclude {name} itself, its subsidiaries, and
generic platforms that only partially overlap. Rank the most significant first.

Search results:
{results}
"""


async def discover_competitors(
    keenable: KeenableClient, profile: CompanyProfile, n: int = config.NUM_COMPETITORS
) -> list[Competitor]:
    queries = [
        f"top competitors of {profile.name}",
        f"best {profile.name} alternatives",
        f"{profile.name} vs competitors comparison",
    ]
    batches = await asyncio.gather(*(keenable.search(q) for q in queries))
    results = [r for batch in batches for r in batch]

    prompt = PROMPT.format(
        name=profile.name,
        website=profile.website,
        industry=profile.industry,
        description=profile.description,
        products=", ".join(profile.main_products),
        n=n,
        results=format_results(results),
    )
    found = await structured_llm(CompetitorList).ainvoke(prompt)
    return found.competitors[:n]
