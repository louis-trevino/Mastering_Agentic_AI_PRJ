"""Offline test fixtures: fake Keenable and fake Groq, so tests spend no tokens or quota.

Every test runs with:
- a FakeKeenable in place of the real MCP client (records each search),
- a FakeLLM in place of every structured_llm() (records each prompt),
- the cache and reports folders redirected to a temp directory,
- ChatGroq made unusable, so an accidental live call fails loudly.
"""

import re

import pytest

import mkt_agent.agents.company_profiler as company_profiler
import mkt_agent.agents.competitor_analysis as competitor_analysis
import mkt_agent.agents.competitor_discovery as competitor_discovery
import mkt_agent.llm as llm
import mkt_agent.orchestrator as orchestrator
from mkt_agent import config
from mkt_agent.schemas import (
    Briefing,
    CompanyProfile,
    Competitor,
    CompetitorCard,
    CompetitorList,
    MarketPositioning,
    NewsItem,
    PricingTier,
)

COMPETITOR_POOL = [
    ("Asana", "asana.com"),
    ("Monday.com", "monday.com"),
    ("Jira", "atlassian.com"),
    ("ClickUp", "clickup.com"),
    ("Wrike", "wrike.com"),
]


class FakeKeenable:
    """Stands in for KeenableClient; returns one synthetic result per search."""

    def __init__(self):
        self.searches: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def search(self, query, *, site=None, max_results=5, published_after=None, snippet_max_length=800):
        self.searches.append({"query": query, "site": site, "published_after": published_after})
        slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
        return [
            {
                "title": f"Result for {query}",
                "url": f"https://{site or 'example.com'}/{slug}",
                "snippet": f"Snippet about {query}",
                "published_at": f"{published_after or '2026-01-01'}T00:00:00Z",
            }
        ]


class FakeLLM:
    """Returns plausible structured outputs per schema; can fail for chosen competitors."""

    def __init__(self):
        self.prompts: list[tuple[str, str]] = []
        self.fail_for: set[str] = set()
        self.rate_limit_error: Exception | None = None  # raised by competitor analyses when set

    def __call__(self, schema, temperature=0.0):
        return _FakeRunnable(self, schema)


class _FakeRunnable:
    def __init__(self, fake: FakeLLM, schema):
        self.fake, self.schema = fake, schema

    async def ainvoke(self, prompt: str):
        self.fake.prompts.append((self.schema.__name__, prompt))
        if self.schema is CompanyProfile:
            return CompanyProfile(
                name="Trello", website="trello.com", industry="Project management software",
                description="Visual kanban boards for teams.", main_products=["Trello"],
            )
        if self.schema is CompetitorList:
            n = int(re.search(r"top (\d+) DIRECT", prompt).group(1))
            return CompetitorList(
                competitors=[Competitor(name=a, website=b, reason="Kanban rival") for a, b in COMPETITOR_POOL[:n]]
            )
        if self.schema is CompetitorCard:
            name = re.search(r"Competitor: (.+?) \(", prompt).group(1)
            if name in self.fake.fail_for:
                raise RuntimeError(f"analysis failed for {name}")
            if self.fake.rate_limit_error:
                raise self.fake.rate_limit_error
            return make_card(name)
        if self.schema is Briefing:
            return Briefing(executive_summary="Summary.", key_takeaways=["Takeaway"], pricing_comparison="Pricing.")
        raise AssertionError(f"unexpected schema {self.schema}")


def make_card(name: str, **overrides) -> CompetitorCard:
    fields = dict(
        name=name,
        website=f"{name.lower()}.com",
        overview=f"{name} overview.",
        pricing=[PricingTier(plan="Pro", price="$10/user/month", details="Everything")],
        pricing_notes="",
        starting_price="$10/user/month",
        free_plan="Yes",
        core_features=["Boards"],
        market_positioning=MarketPositioning(
            target_segment="SMB teams", value_proposition="Simple", differentiators=[f"{name} differentiator"]
        ),
        recent_news=[NewsItem(date="2026-10-01", headline=f"{name} launches AI", summary="New.", url="https://x.com")],
        strengths=["Fast"],
        weaknesses=["Pricey"],
    )
    fields.update(overrides)
    return CompetitorCard(**fields)


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(config, "GROQ_API_KEY", "test")
    monkeypatch.setattr(config, "KEENABLE_API_KEY", "test")

    def no_live_groq(*args, **kwargs):
        raise AssertionError("Tests must not call Groq")

    monkeypatch.setattr(llm, "ChatGroq", no_live_groq)


@pytest.fixture
def fake_keenable(monkeypatch) -> FakeKeenable:
    fake = FakeKeenable()
    monkeypatch.setattr(orchestrator, "KeenableClient", lambda: fake)
    return fake


@pytest.fixture
def fake_llm(monkeypatch) -> FakeLLM:
    fake = FakeLLM()
    for module in (company_profiler, competitor_discovery, competitor_analysis, orchestrator):
        monkeypatch.setattr(module, "structured_llm", fake)
    return fake
