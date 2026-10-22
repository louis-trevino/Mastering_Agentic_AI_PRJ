"""Agent 3 - Competitor Analysis: turns a raw dossier into a structured competitor card."""

from ..keenable import format_results
from ..llm import structured_llm
from ..schemas import CompanyProfile, Competitor, CompetitorCard

PROMPT = """You are a competitive intelligence analyst preparing a competitor card
for {company} ({industry}).

Competitor: {name} ({website})
Why it competes: {reason}

Extract pricing, core features, market positioning and recent news for {name}
using ONLY the research data below. Rules:
- Do not invent prices. If no pricing is found, return pricing [] and explain in pricing_notes.
- recent_news: only items about {name} from the NEWS section, newest first, max 5,
  with URLs copied exactly from the data.
- Strengths and weaknesses are relative to {company}.

=== PRICING ===
{pricing}

=== FEATURES ===
{features}

=== POSITIONING / REVIEWS ===
{positioning}

=== NEWS (recent) ===
{news}
"""


async def analyze_competitor(
    profile: CompanyProfile, competitor: Competitor, dossier: dict[str, list[dict]]
) -> CompetitorCard:
    prompt = PROMPT.format(
        company=profile.name,
        industry=profile.industry,
        name=competitor.name,
        website=competitor.website or "unknown",
        reason=competitor.reason,
        **{topic: format_results(results) for topic, results in dossier.items()},
    )
    return await structured_llm(CompetitorCard).ainvoke(prompt)
