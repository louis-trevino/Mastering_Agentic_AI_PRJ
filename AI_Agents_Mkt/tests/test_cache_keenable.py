"""Disk cache, cached LLM wrapper, and the Keenable client's caching/throttling/retries."""

import asyncio
import json
import time
from types import SimpleNamespace

import pytest

from mkt_agent import cache, config, keenable
from mkt_agent.keenable import KeenableClient
from mkt_agent.llm import CachedStructuredLLM
from mkt_agent.schemas import Briefing


def test_cache_put_get_and_disable():
    cache.put("ns", "k", {"a": 1})
    assert cache.get("ns", "k") == {"a": 1}
    assert cache.get("ns", "missing") is None
    with cache.enabled(False):
        assert cache.get("ns", "k") is None
        cache.put("ns", "other", 1)
    assert cache.get("ns", "other") is None


def test_cache_entries_expire(monkeypatch):
    cache.put("ns", "k", "value")
    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() + config.CACHE_TTL_HOURS * 3600 + 1)
    assert cache.get("ns", "k") is None


def test_cache_ignores_corrupt_entries():
    path = config.CACHE_DIR / "ns" / "k.json"
    path.parent.mkdir(parents=True)
    path.write_text("garbage", encoding="utf-8")
    assert cache.get("ns", "k") is None


def test_cache_clear():
    cache.put("a", "1", 1)
    cache.put("b", "2", 2)
    assert cache.clear() == 2
    assert cache.get("a", "1") is None


class CountingRunnable:
    def __init__(self):
        self.calls = 0

    async def ainvoke(self, prompt):
        self.calls += 1
        return Briefing(executive_summary=prompt, key_takeaways=[], pricing_comparison="")


def test_cached_llm_reuses_outputs_per_prompt():
    inner = CountingRunnable()
    llm = CachedStructuredLLM(inner, Briefing, temperature=0.0)

    first = asyncio.run(llm.ainvoke("prompt A"))
    again = asyncio.run(llm.ainvoke("prompt A"))
    other = asyncio.run(llm.ainvoke("prompt B"))

    assert inner.calls == 2
    assert first == again and isinstance(again, Briefing)
    assert other.executive_summary == "prompt B"


class FakeSession:
    """Mimics mcp.ClientSession.call_tool; can fail the first N calls with a rate-limit error."""

    def __init__(self, rate_limited_calls=0, error_result=False):
        self.calls = []
        self.rate_limited_calls = rate_limited_calls
        self.error_result = error_result

    async def call_tool(self, tool, args):
        self.calls.append((tool, args))
        if len(self.calls) <= self.rate_limited_calls:
            raise RuntimeError("Too many requests — your organization has a 10 RPS limit.")
        text = "boom" if self.error_result else json.dumps({"results": [{"title": "t", "url": "u"}]})
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)], is_error=self.error_result
        )


def client_with(session) -> KeenableClient:
    client = KeenableClient(api_key="test")
    client._session = session
    return client


@pytest.fixture
def fast(monkeypatch):
    """No real sleeping or throttling delays."""
    monkeypatch.setattr(config, "KEENABLE_MAX_RPS", 10_000)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(keenable.asyncio, "sleep", no_sleep)


def test_search_results_are_cached(fast):
    session = FakeSession()
    client = client_with(session)

    asyncio.run(client.search("q", site="a.com"))
    results = asyncio.run(client.search("q", site="a.com"))
    asyncio.run(client.search("q", site="b.com"))  # different args -> new call

    assert results == [{"title": "t", "url": "u"}]
    assert len(session.calls) == 2
    with cache.enabled(False):
        asyncio.run(client.search("q", site="a.com"))
    assert len(session.calls) == 3


def test_search_retries_after_rate_limit(fast):
    session = FakeSession(rate_limited_calls=2)
    results = asyncio.run(client_with(session).search("q"))
    assert results and len(session.calls) == 3


def test_search_gives_up_after_max_retries(fast):
    session = FakeSession(rate_limited_calls=99)
    with pytest.raises(RuntimeError, match="Too many requests"):
        asyncio.run(client_with(session).search("q"))
    assert len(session.calls) == keenable.KEENABLE_RETRIES


def test_tool_error_results_raise_without_retry(fast):
    session = FakeSession(error_result=True)
    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(client_with(session).search("q"))
    assert len(session.calls) == 1


def test_throttle_spaces_out_requests(monkeypatch):
    monkeypatch.setattr(config, "KEENABLE_MAX_RPS", 50)  # 20 ms apart
    client = client_with(FakeSession())

    async def burst():
        start = time.monotonic()
        await asyncio.gather(*(client.search(f"q{i}") for i in range(6)))
        return time.monotonic() - start

    assert asyncio.run(burst()) >= 5 * 0.02 * 0.9
