"""Orchestrator Agent: coordinates the research pipeline as a LangGraph graph.

    START -> profile_company -> discover_competitors -> review_competitors (human-in-the-loop)
          --(fan-out, one per competitor)--> research_competitor [Agent 2 reporter -> Agent 3 analysis]
          -> compile_briefing -> END

When review is enabled, review_competitors pauses the graph with interrupt() so a
person can edit the discovered competitors; the run is resumed with the approved list.
The pipeline stops after the briefing is produced: it takes no business actions.
"""

import json
import operator
from typing import Annotated, AsyncIterator, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send, interrupt

from . import config, schemas
from .agents import analyze_competitor, discover_competitors, gather_dossier, profile_company
from .keenable import KeenableClient
from .llm import structured_llm
from .schemas import Briefing, CompanyProfile, Competitor, CompetitorReport


class ResearchState(TypedDict, total=False):
    company: str
    website: str
    num_competitors: int
    news_days: int
    review: bool  # pause for human review of the discovered competitors
    profile: CompanyProfile
    competitors: list[Competitor]
    reports: Annotated[list[CompetitorReport], operator.add]  # filled in parallel
    briefing: Briefing


class CompetitorTask(TypedDict):
    rank: int
    profile: CompanyProfile
    competitor: Competitor
    news_days: int


BRIEFING_PROMPT = """You are the lead analyst compiling a competitive briefing for {name}
({industry}): {description}

Below are the competitor analysis cards produced by your team. Write the briefing
using ONLY this material. Be specific and concrete.

{cards}
"""


def build_graph(keenable: KeenableClient, checkpointer: BaseCheckpointSaver | None = None):
    async def profile_node(state: ResearchState) -> dict:
        return {"profile": await profile_company(keenable, state["company"], state.get("website", ""))}

    async def discover_node(state: ResearchState) -> dict:
        n = state.get("num_competitors", config.NUM_COMPETITORS)
        return {"competitors": await discover_competitors(keenable, state["profile"], n)}

    def review_node(state: ResearchState) -> dict:
        if not state.get("review"):
            return {}
        # Pauses the run; resumes with the approved list of {"name", "website", "reason"} dicts
        approved = interrupt(
            {
                "profile": state["profile"].model_dump(),
                "competitors": [c.model_dump() for c in state["competitors"]],
            }
        )
        return {"competitors": [Competitor.model_validate(c) for c in approved]}

    def fan_out(state: ResearchState) -> list[Send]:
        news_days = state.get("news_days", config.NEWS_LOOKBACK_DAYS)
        return [
            Send(
                "research_competitor",
                {"rank": i, "profile": state["profile"], "competitor": c, "news_days": news_days},
            )
            for i, c in enumerate(state["competitors"], 1)
        ]

    async def research_node(task: CompetitorTask) -> dict:
        report = CompetitorReport(rank=task["rank"], competitor=task["competitor"])
        try:
            dossier = await gather_dossier(
                keenable, task["competitor"], task["profile"].industry, task["news_days"]
            )
            report.sources = list(dict.fromkeys(r["url"] for results in dossier.values() for r in results))
            report.card = await analyze_competitor(task["profile"], task["competitor"], dossier)
        except Exception as e:  # one failed competitor shouldn't stop the others
            report.error = f"{type(e).__name__}: {e}"
        return {"reports": [report]}

    async def compile_node(state: ResearchState) -> dict:
        profile = state["profile"]
        cards = [r.card.model_dump() for r in sorted(state["reports"], key=lambda r: r.rank) if r.card]
        if not cards:
            raise RuntimeError("No competitor could be analyzed; see the report errors.")
        prompt = BRIEFING_PROMPT.format(
            name=profile.name,
            industry=profile.industry,
            description=profile.description,
            cards=json.dumps(cards, indent=1),
        )
        return {"briefing": await structured_llm(Briefing, temperature=0.2).ainvoke(prompt)}

    graph = StateGraph(ResearchState)
    graph.add_node("profile_company", profile_node)
    graph.add_node("discover_competitors", discover_node)
    graph.add_node("review_competitors", review_node)
    graph.add_node("research_competitor", research_node)
    graph.add_node("compile_briefing", compile_node)

    graph.add_edge(START, "profile_company")
    graph.add_edge("profile_company", "discover_competitors")
    graph.add_edge("discover_competitors", "review_competitors")
    graph.add_conditional_edges("review_competitors", fan_out, ["research_competitor"])
    graph.add_edge("research_competitor", "compile_briefing")
    graph.add_edge("compile_briefing", END)
    return graph.compile(checkpointer=checkpointer)


def make_checkpointer() -> InMemorySaver:
    """In-memory checkpointer that lets a run pause for review and resume.

    Our Pydantic state types are allow-listed so LangGraph will deserialize them."""
    allowed = [(schemas.__name__, cls.__name__) for cls in (CompanyProfile, Competitor, CompetitorReport, Briefing)]
    return InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=allowed))


def research_inputs(
    company: str,
    website: str = "",
    *,
    num_competitors: int = config.NUM_COMPETITORS,
    news_days: int = config.NEWS_LOOKBACK_DAYS,
    review: bool = False,
) -> ResearchState:
    return {
        "company": company,
        "website": website,
        "num_competitors": num_competitors,
        "news_days": news_days,
        "review": review,
    }


async def stream_research(
    inputs: ResearchState | None = None,
    *,
    resume: list[dict] | None = None,
    thread_id: str = "default",
    checkpointer: BaseCheckpointSaver | None = None,
) -> AsyncIterator[tuple[str, dict]]:
    """Start a run (`inputs`) or resume a paused one (`resume` = approved competitors).

    Yields ("update", {node: output}) per finished step, then either
    ("review", {"profile", "competitors"}) when paused for review, or ("done", final_state).
    Pausing for review requires a checkpointer, and resuming needs the same checkpointer
    and thread_id.
    """
    config.check_config()
    if (inputs is None) == (resume is None):
        raise ValueError("Pass either inputs or resume")
    run_config = {"configurable": {"thread_id": thread_id}}
    payload = Command(resume=resume) if resume is not None else inputs

    async with KeenableClient() as keenable:
        graph = build_graph(keenable, checkpointer)
        final_state: dict = {}
        async for mode, data in graph.astream(payload, run_config, stream_mode=["updates", "values"]):
            if mode == "values":
                final_state = data
            elif "__interrupt__" in data:
                yield "review", data["__interrupt__"][0].value
                return
            else:
                yield "update", data
        final_state["reports"] = sorted(final_state.get("reports", []), key=lambda r: r.rank)
        yield "done", final_state


async def run_research(company: str, website: str = "", **settings) -> dict:
    """Run the whole pipeline without review and return the final state."""
    final_state: dict = {}
    async for kind, data in stream_research(research_inputs(company, website, **settings)):
        if kind == "done":
            final_state = data
    return final_state
