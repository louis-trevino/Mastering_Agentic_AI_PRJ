# Marketing Research Agent

## Project Description

### The Marketing Research Agent

By Luis C Trevino 2026.

The Marketing Research Agent runs a competitive market research pipeline for a company. It discovers the company's top competitors, gathers fresh web and news data about each one with the Keenable search engine, and turns the findings into structured competitor analysis cards plus a briefing.

The workflow stops once the report is produced. It does not send emails, save to databases or take any business action.

Built with Python, LangGraph, LangChain, Groq (`openai/gpt-oss-120b`), the Keenable Search API (over MCP) and Streamlit.

## Agents

| Agent | Role |
|---|---|
| Company Profiler | Identifies the target company (industry, products) so discovery searches for the right business |
| Agent 1: Competitor Discovery | Finds the company's top competitors with Keenable searches |
| Competitor review (human-in-the-loop) | Pauses the run so you can edit, add or remove competitors before research starts (optional) |
| Agent 2: Competitor Reporter | Runs targeted Keenable searches per competitor: pricing, features, reviews and recent news |
| Agent 3: Competitor Analysis | Extracts pricing, core features, market positioning, recent news, strengths and weaknesses into a structured card |
| Orchestrator | LangGraph graph that coordinates the pipeline, researches competitors in parallel and compiles the briefing |

```
profile_company -> discover_competitors -> review_competitors -> research_competitor (x N, parallel) -> compile_briefing
```

## Setup

```
uv sync
```

Add your API keys to a `.env` file in this folder:

```
GROQ_API_KEY=...
KEENABLE_API_KEY=...
```

Optionally, set `GROQ_MODEL` to use a different Groq model (default `openai/gpt-oss-120b`).

## Run the Streamlit App

```
streamlit run app.py
```

The sidebar has four settings:
- the number of competitors (1-5)
- the news window (7-365 days)
- whether to review the competitors before the research runs
- whether to use cached results

The briefing includes a "Comparison at a glance" table across competitors (starting price, free plan, target segment, key differentiator and latest news), followed by one detailed card per competitor.

Every finished briefing is saved to `reports/` as Markdown + JSON. Past briefings can be reopened from the sidebar and downloaded as Markdown or JSON.

## Caching

Keenable search results and LLM outputs are cached in `.cache/mkt_agent/` for 6 hours. If you research the same company again within that window, the run reuses them and costs no Groq tokens or Keenable requests. To force fresh research, turn off "Use cached results" in the sidebar, pass `--no-cache` on the command line, or click "Clear cache".

## Run from the Command Line

```
py -m mkt_agent "Notion" notion.com
py -m mkt_agent "Linear" -n 2 --news-days 30 --review
```

The briefing is printed as Markdown to stdout, and progress goes to stderr. It is also saved to `reports/`; use `--no-save` to skip that and `--no-cache` to force fresh research.

## Run the Tests

The test suite replaces Groq and Keenable with fakes, so it makes no network calls and spends no tokens. It covers the pipeline (including the review pause and resume), report rendering, saving, caching, Keenable throttling and retries, and the Streamlit UI flow.

```
uv sync
uv run pytest
```

## Limits

- **Groq free tier:** `openai/gpt-oss-120b` allows 8k tokens/minute and 200k tokens/day. A run with 3 competitors uses about 40k tokens and takes 2-3 minutes, so you get about 5 runs per day.
- **Keenable:** 10 requests/second per organization. The client throttles itself to 8/second and retries when a request is rejected.

## Sample Input

Company: `Notion`, website: `notion.com`
