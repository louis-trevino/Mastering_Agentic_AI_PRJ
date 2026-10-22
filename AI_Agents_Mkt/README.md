# Marketing Research Agent

## Project Description

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

The sidebar has three settings:
- the number of competitors (1-5)
- the news window (7-365 days)
- whether to review the competitors before the research runs

Results can be downloaded as Markdown or JSON.

## Run from the Command Line

```
py -m mkt_agent "Notion" notion.com
py -m mkt_agent "Linear" -n 2 --news-days 30 --review
```

The briefing is printed as Markdown to stdout, and progress goes to stderr.

## Limits

- **Groq free tier:** `openai/gpt-oss-120b` allows 8k tokens/minute and 200k tokens/day. A run with 3 competitors uses about 40k tokens and takes 2-3 minutes, so you get about 5 runs per day.
- **Keenable:** 10 requests/second per organization. The client throttles itself to 8/second and retries when a request is rejected.

## Sample Input

Company: `Notion`, website: `notion.com`
