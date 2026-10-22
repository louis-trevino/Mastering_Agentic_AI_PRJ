"""Structured outputs produced by the agents.

Every field is required (no defaults) so the schemas work with Groq's strict
JSON-schema mode; agents use "" or [] when information is unavailable.
"""

from typing import Literal

from pydantic import BaseModel, Field


class CompanyProfile(BaseModel):
    name: str = Field(description="Official company name")
    website: str = Field(description="Primary website domain, e.g. notion.so")
    industry: str = Field(description="Industry / market category")
    description: str = Field(description="2-3 sentence description of what the company does")
    main_products: list[str] = Field(description="Main products or services")


class Competitor(BaseModel):
    name: str
    website: str = Field(description="Primary website domain, e.g. clickup.com, or '' if unknown")
    reason: str = Field(description="One sentence on why this is a direct competitor")


class CompetitorList(BaseModel):
    competitors: list[Competitor] = Field(description="Top direct competitors, most significant first")


class PricingTier(BaseModel):
    plan: str
    price: str = Field(description="Price as stated, e.g. '$10/user/month', 'Free', 'Contact sales'")
    details: str = Field(description="What the plan includes, briefly")


class NewsItem(BaseModel):
    date: str = Field(description="YYYY-MM-DD, or '' if unknown")
    headline: str
    summary: str = Field(description="One sentence summary")
    url: str = Field(description="Source URL, copied exactly from the research data")


class MarketPositioning(BaseModel):
    target_segment: str = Field(description="Who the product is for")
    value_proposition: str
    differentiators: list[str]


class CompetitorCard(BaseModel):
    name: str
    website: str
    overview: str = Field(description="2-3 sentence overview of the company and its offering")
    pricing: list[PricingTier] = Field(description="Pricing tiers found in the research; [] if none")
    pricing_notes: str = Field(description="Pricing model notes or caveats, e.g. 'pricing not public'")
    starting_price: str = Field(
        description="Cheapest PAID plan price as stated, e.g. '$10/user/month'; 'Contact sales' or 'Unknown' if not public"
    )
    free_plan: Literal["Yes", "No", "Free trial only", "Unknown"]
    core_features: list[str] = Field(description="5-8 core product features")
    market_positioning: MarketPositioning
    recent_news: list[NewsItem] = Field(description="Most relevant recent news, newest first; [] if none")
    strengths: list[str]
    weaknesses: list[str]


class CompetitorReport(BaseModel):
    """Pipeline record for one competitor (assembled in code, not by the LLM)."""

    rank: int
    competitor: Competitor
    card: CompetitorCard | None = None
    sources: list[str] = []
    error: str = ""


class Briefing(BaseModel):
    executive_summary: str = Field(description="One paragraph summary of the competitive landscape")
    key_takeaways: list[str] = Field(description="4-6 bullet-point takeaways for the target company")
    pricing_comparison: str = Field(description="Short comparison of competitor pricing approaches")
