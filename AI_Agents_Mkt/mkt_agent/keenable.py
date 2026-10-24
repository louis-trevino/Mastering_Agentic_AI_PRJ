"""Async client for the Keenable search engine, spoken to over MCP (streamable HTTP)."""

import asyncio
import json
import time
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

from . import cache, config

KEENABLE_RETRIES = 4


class KeenableClient:
    """One MCP session shared by every agent during a pipeline run.

    Usage:
        async with KeenableClient() as keenable:
            results = await keenable.search("query", site="example.com")
    """

    def __init__(self, api_key: str | None = None, url: str = config.KEENABLE_MCP_URL):
        self._api_key = api_key or config.KEENABLE_API_KEY
        self._url = url
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._throttle_lock = asyncio.Lock()
        self._last_request = 0.0

    async def __aenter__(self) -> "KeenableClient":
        self._stack = AsyncExitStack()
        http_client = await self._stack.enter_async_context(
            create_mcp_http_client(headers={"X-API-Key": self._api_key})
        )
        streams = await self._stack.enter_async_context(
            streamable_http_client(self._url, http_client=http_client)
        )
        self._session = await self._stack.enter_async_context(ClientSession(streams[0], streams[1]))
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc) -> None:
        if self._stack:
            await self._stack.aclose()
        self._stack = self._session = None

    async def _throttle(self) -> None:
        """Space out request starts to stay under Keenable's per-second limit."""
        async with self._throttle_lock:
            wait = self._last_request + 1 / config.KEENABLE_MAX_RPS - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = time.monotonic()

    async def _call(self, tool: str, args: dict) -> str:
        if not self._session:
            raise RuntimeError("KeenableClient must be used inside 'async with'")
        for attempt in range(1, KEENABLE_RETRIES + 1):
            await self._throttle()
            try:
                result = await self._session.call_tool(tool, args)
                text = "".join(c.text for c in result.content if c.type == "text")
                if result.is_error:
                    raise RuntimeError(f"Keenable {tool} failed: {text}")
                return text
            except Exception as e:  # rate limits arrive as MCPError or as an error result
                if "too many requests" not in str(e).lower() or attempt == KEENABLE_RETRIES:
                    raise
                await asyncio.sleep(attempt * 1.5)

    async def search(
        self,
        query: str,
        *,
        site: str | None = None,
        max_results: int = config.SEARCH_MAX_RESULTS,
        published_after: str | None = None,
        snippet_max_length: int = config.SNIPPET_MAX_LENGTH,
    ) -> list[dict]:
        """Return result dicts with title, url, snippet, published_at."""
        args = {
            "query": query,
            "max_results": max_results,
            "snippet_max_length": snippet_max_length,
            "output_format": "json",
        }
        if site:
            args["site"] = site
        if published_after:
            args["published_after"] = published_after

        key = cache.make_key(args)
        cached = cache.get("keenable", key)
        if cached is not None:
            return cached
        results = json.loads(await self._call("search_web_pages", args)).get("results", [])
        cache.put("keenable", key, results)
        return results

    async def fetch(self, url: str, *, prompt: str | None = None, max_chars: int = 20000) -> str:
        """Return a page as markdown, or only the part matching `prompt` when given."""
        args = {"url": url, "max_chars": max_chars}
        if prompt:
            args["prompt"] = prompt
        return await self._call("fetch_page_content", args)


def format_results(results: list[dict]) -> str:
    """Render search results as compact text for an LLM prompt."""
    if not results:
        return "(no results)"
    lines = []
    for r in results:
        date = (r.get("published_at") or "")[:10] or "n/a"
        snippet = " ".join((r.get("snippet") or r.get("description") or "").split())
        lines.append(f"- [{date}] {r.get('title')}\n  URL: {r.get('url')}\n  {snippet}")
    return "\n".join(lines)
