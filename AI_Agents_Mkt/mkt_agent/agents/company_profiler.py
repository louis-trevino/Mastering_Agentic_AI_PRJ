"""Company Profiler (support subagent): pins down who the target company is
before competitors are searched, so discovery isn't thrown off by ambiguous names."""

import asyncio

from ..keenable import KeenableClient, format_results
from ..llm import structured_llm
from ..schemas import CompanyProfile

PROMPT = """You are a market research analyst. Using ONLY the search results below,
build a short profile of the company "{company}".{website_hint}

Search results:
{results}
"""


async def profile_company(keenable: KeenableClient, company: str, website: str = "") -> CompanyProfile:
    searches = [keenable.search(f"{company} company overview: what it does, products and customers")]
    if website:
        searches.append(keenable.search(f"{company} products and platform", site=website))
    results = [r for batch in await asyncio.gather(*searches) for r in batch]

    website_hint = f' Its website is "{website}".' if website else ""
    prompt = PROMPT.format(company=company, website_hint=website_hint, results=format_results(results))
    return await structured_llm(CompanyProfile).ainvoke(prompt)
