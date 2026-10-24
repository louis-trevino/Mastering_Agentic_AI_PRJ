"""End-to-end pipeline tests (LangGraph graph with fake Keenable + fake LLM)."""

import asyncio
from contextlib import aclosing
from datetime import date, timedelta

import groq
import httpx
import pytest

from mkt_agent import make_checkpointer, research_inputs, run_research, stream_research


async def collect(**stream_args) -> list[tuple[str, dict]]:
    events = stream_research(**stream_args)
    async with aclosing(events):
        return [event async for event in events]


def test_full_run_without_review(fake_keenable, fake_llm):
    state = asyncio.run(run_research("Trello", "trello.com"))

    assert state["profile"].name == "Trello"
    assert [(r.rank, r.competitor.name) for r in state["reports"]] == [(1, "Asana"), (2, "Monday.com"), (3, "Jira")]
    assert all(r.card and not r.error and r.sources for r in state["reports"])
    assert state["briefing"].executive_summary == "Summary."
    assert state["generated_at"].startswith(date.today().isoformat())


def test_streams_progress_events_in_order(fake_keenable, fake_llm):
    events = asyncio.run(collect(inputs=research_inputs("Trello", num_competitors=2)))

    kinds = [kind for kind, _ in events]
    nodes = [node for kind, data in events if kind == "update" for node in data]
    assert kinds[-1] == "done"
    assert nodes[:3] == ["profile_company", "discover_competitors", "review_competitors"]
    assert nodes.count("research_competitor") == 2
    assert nodes[-1] == "compile_briefing"


@pytest.mark.parametrize("n", [1, 5])
def test_number_of_competitors_setting(fake_keenable, fake_llm, n):
    state = asyncio.run(run_research("Trello", num_competitors=n))
    assert len(state["reports"]) == n


def test_news_window_setting(fake_keenable, fake_llm):
    asyncio.run(run_research("Trello", num_competitors=2, news_days=30))

    since = (date.today() - timedelta(days=30)).isoformat()
    news_searches = [s for s in fake_keenable.searches if s["published_after"]]
    assert len(news_searches) == 2
    assert all(s["published_after"] == since for s in news_searches)


def test_offsite_queries_name_domain_and_industry(fake_keenable, fake_llm):
    """Disambiguation: 'Coda' (coda.io) must not be confused with Coda Payments."""
    asyncio.run(run_research("Trello", num_competitors=1))

    asana = [s for s in fake_keenable.searches if "Asana" in s["query"]]
    onsite = [s for s in asana if s["site"] == "asana.com"]
    offsite = [s for s in asana if s["site"] is None]
    assert len(onsite) == 2 and len(offsite) == 2
    assert all("(asana.com) Project management software" in s["query"] for s in offsite)


def test_review_pauses_then_resumes_with_edited_list(fake_keenable, fake_llm):
    checkpointer = make_checkpointer()
    first = asyncio.run(
        collect(
            inputs=research_inputs("Trello", num_competitors=3, review=True),
            thread_id="t1",
            checkpointer=checkpointer,
        )
    )
    kind, proposal = first[-1]
    assert kind == "review"
    assert proposal["profile"]["name"] == "Trello"
    assert [c["name"] for c in proposal["competitors"]] == ["Asana", "Monday.com", "Jira"]
    assert not any(name == "CompetitorCard" for name, _ in fake_llm.prompts)  # nothing researched yet

    edited = [proposal["competitors"][2], {"name": "Wrike", "website": "wrike.com", "reason": "Added by reviewer"}]
    second = asyncio.run(collect(resume=edited, thread_id="t1", checkpointer=checkpointer))
    kind, state = second[-1]
    assert kind == "done"
    assert [(r.rank, r.competitor.name) for r in state["reports"]] == [(1, "Jira"), (2, "Wrike")]
    # profiling/discovery were not repeated on resume
    assert [name for name, _ in fake_llm.prompts].count("CompetitorList") == 1


def test_failed_competitor_is_reported_without_stopping_the_run(fake_keenable, fake_llm):
    fake_llm.fail_for = {"Monday.com"}
    state = asyncio.run(run_research("Trello"))

    by_name = {r.competitor.name: r for r in state["reports"]}
    assert by_name["Monday.com"].card is None
    assert "analysis failed for Monday.com" in by_name["Monday.com"].error
    assert by_name["Asana"].card and by_name["Jira"].card
    assert state["briefing"] is not None


def test_run_fails_when_no_competitor_could_be_analyzed(fake_keenable, fake_llm):
    fake_llm.fail_for = {"Asana"}
    with pytest.raises(RuntimeError, match="No competitor could be analyzed"):
        asyncio.run(run_research("Trello", num_competitors=1))


def test_groq_rate_limit_stops_the_run_with_the_real_cause(fake_keenable, fake_llm):
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com"))
    fake_llm.rate_limit_error = groq.RateLimitError("tokens per day (TPD)", response=response, body=None)
    with pytest.raises(groq.RateLimitError):
        asyncio.run(run_research("Trello"))


def test_stream_research_requires_inputs_or_resume(fake_keenable, fake_llm):
    with pytest.raises(ValueError):
        asyncio.run(collect())
