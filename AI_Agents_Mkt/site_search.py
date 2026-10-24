"""
Site Search - query a specific website through the Keenable MCP server.

Iteration 1: ask for a website and a query, run a Keenable search restricted
to that site, and print the matching results (title, date, URL, snippet).

Requires KEENABLE_API_KEY in the .env file next to this script.
"""

import asyncio
import json
import os
import textwrap
from urllib.parse import urlparse

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

KEENABLE_MCP_URL = "https://api.keenable.ai/mcp"
MAX_RESULTS = 5
SNIPPET_WIDTH = 100
SNIPPET_MAX_CHARS = 400


def normalize_site(raw: str) -> str:
    """Turn user input like 'https://www.techcrunch.com/foo' into 'techcrunch.com'."""
    raw = raw.strip()
    if "://" not in raw:
        raw = "https://" + raw
    host = urlparse(raw).hostname or ""
    return host.removeprefix("www.")


async def search_site(session: ClientSession, site: str, query: str) -> list[dict]:
    """Run a Keenable search restricted to one site and return the result dicts."""
    result = await session.call_tool(
        "search_web_pages",
        {"query": query, "site": site, "max_results": MAX_RESULTS, "output_format": "json"},
    )
    text = "".join(c.text for c in result.content if c.type == "text")
    if result.is_error:
        raise RuntimeError(text or "Keenable returned an error")
    return json.loads(text).get("results", [])


def print_results(results: list[dict]) -> None:
    if not results:
        print("\nNo results found.\n")
        return

    print()
    for i, r in enumerate(results, 1):
        date = (r.get("published_at") or "")[:10] or "n/a"
        print(f"{i}. {r.get('title') or '(untitled)'}")
        print(f"   Date: {date}")
        print(f"   URL:  {r.get('url')}")
        snippet = " ".join((r.get("snippet") or r.get("description") or "").split())
        if len(snippet) > SNIPPET_MAX_CHARS:
            snippet = snippet[:SNIPPET_MAX_CHARS].rstrip() + "..."
        if snippet:
            print(textwrap.fill(snippet, SNIPPET_WIDTH, initial_indent="   ", subsequent_indent="   "))
        print()


async def prompt(text: str) -> str:
    # input() blocks, so run it in a thread to keep the MCP session's event loop alive
    return (await asyncio.to_thread(input, text)).strip()


async def main() -> None:
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    api_key = os.getenv("KEENABLE_API_KEY")
    if not api_key:
        raise SystemExit("KEENABLE_API_KEY is not set (add it to your .env file).")

    http_client = create_mcp_http_client(headers={"X-API-Key": api_key})
    async with http_client, streamable_http_client(KEENABLE_MCP_URL, http_client=http_client) as streams:
        read_stream, write_stream = streams[0], streams[1]
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("Connected to Keenable. Press Enter on an empty website to quit.\n")

            while True:
                site = normalize_site(await prompt("Website (e.g. techcrunch.com): "))
                if not site:
                    break
                query = await prompt("Query: ")
                if not query:
                    print("Query cannot be empty.\n")
                    continue

                print(f"\nSearching {site} for: {query}")
                try:
                    print_results(await search_site(session, site, query))
                except Exception as e:
                    print(f"Search failed: {e}\n")

    print("Bye.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBye.")
