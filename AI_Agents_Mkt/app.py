"""Streamlit UI for the Marketing Research Agent.

Run with:  streamlit run app.py

Flow: enter a company -> the agents profile it and discover competitors -> (optional)
review/edit the competitor list -> research + analysis -> briefing (auto-saved to reports/).
"""

import asyncio
import json
import time
import uuid
from contextlib import aclosing

import groq
import streamlit as st

from mkt_agent import briefing_markdown, cache, config, make_checkpointer, research_inputs, stream_research
from mkt_agent.report import card_markdown, comparison_rows
from mkt_agent.storage import list_reports, load_report, save_report, slugify, state_to_dict

st.set_page_config(page_title="Marketing Research Agent", page_icon="🔎", layout="wide")

STEP_LABELS = {
    "profile_company": "Company Profiler: profiled the target company",
    "discover_competitors": "Agent 1 - Competitor Discovery: found competitors",
    "review_competitors": "Competitor list approved",
    "research_competitor": "Agents 2+3 - Reporter & Analysis: finished a competitor card",
    "compile_briefing": "Orchestrator: compiled the briefing",
}

ss = st.session_state
ss.setdefault("phase", "input")  # input -> review -> done


def reset() -> None:
    for key in ("phase", "proposal", "result", "saved_path", "thread_id", "checkpointer"):
        ss.pop(key, None)
    ss.phase = "input"


async def run_pipeline(status, **stream_args) -> tuple[str, dict]:
    """Drive one leg of the pipeline, logging progress into `status`.
    Returns ("review", proposal) or ("done", final_state)."""
    start = time.perf_counter()
    # aclosing() shuts the stream (and its Keenable connection) down in this task when we return early;
    # otherwise the generator is finalized later from another task and MCP's cleanup fails
    events = stream_research(
        thread_id=ss.thread_id, checkpointer=ss.checkpointer, use_cache=ss.use_cache, **stream_args
    )
    async with aclosing(events):
        async for kind, data in events:
            if kind != "update":
                return kind, data
            for node, output in data.items():
                elapsed = f"[{time.perf_counter() - start:.0f}s]"
                if node == "discover_competitors":
                    names = ", ".join(c.name for c in output["competitors"])
                    status.write(f"{elapsed} {STEP_LABELS[node]}: **{names}**")
                elif node == "research_competitor":
                    report = output["reports"][0]
                    outcome = "done" if report.card else f"failed ({report.error})"
                    status.write(f"{elapsed} {STEP_LABELS[node]}: **{report.competitor.name}** {outcome}")
                else:
                    status.write(f"{elapsed} {STEP_LABELS.get(node, node)}")
    raise RuntimeError("Pipeline ended without a result")


def run_leg(label: str, **stream_args) -> None:
    """Run a pipeline leg inside a status box and move to the next phase."""
    with st.status(label, expanded=True) as status:
        try:
            kind, data = asyncio.run(run_pipeline(status, **stream_args))
        except groq.RateLimitError as e:
            status.update(label="Research failed: Groq rate limit", state="error")
            st.error(
                "Groq's rate limit was reached. On the free tier, `openai/gpt-oss-120b` allows "
                "200k tokens/day (about 5 runs of 3 competitors). Details:\n\n" + str(e)
            )
            return
        except Exception as e:
            status.update(label="Research failed", state="error")
            st.exception(e)
            return
        status.update(label="Done", state="complete", expanded=False)
    if kind == "review":
        ss.phase, ss.proposal = "review", data
    else:
        ss.phase, ss.result = "done", data
        ss.saved_path = save_report(data)
    st.rerun()


def show_review() -> None:
    profile, competitors = ss.proposal["profile"], ss.proposal["competitors"]
    st.subheader("Review competitors")
    st.write(
        f"**{profile['name']}** ({profile['website']}) was profiled as **{profile['industry']}**: "
        f"{profile['description']}"
    )
    st.caption(
        "Edit, add or delete rows, then approve. A website domain helps the agents find the right company. "
        f"Max {config.MAX_COMPETITORS} competitors."
    )
    edited = st.data_editor(
        competitors,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "name": st.column_config.TextColumn("Competitor", required=True),
            "website": st.column_config.TextColumn("Website (domain)"),
            "reason": st.column_config.TextColumn("Why it competes", width="large"),
        },
        key="competitor_editor",
    )
    approved = [
        {"name": r["name"].strip(), "website": (r.get("website") or "").strip(), "reason": (r.get("reason") or "").strip()}
        for r in edited
        if (r.get("name") or "").strip()
    ]

    col1, col2, _ = st.columns([1, 1, 4])
    if col1.button("Approve & research", type="primary", disabled=not approved):
        if len(approved) > config.MAX_COMPETITORS:
            st.error(f"Please keep at most {config.MAX_COMPETITORS} competitors.")
        else:
            run_leg(f"Researching {len(approved)} competitors... (usually 1-3 minutes)", resume=approved)
    if col2.button("Start over"):
        reset()
        st.rerun()


def show_results(state: dict) -> None:
    profile, briefing = state["profile"], state.get("briefing")
    reports = state.get("reports", [])
    st.header(f"Competitive Briefing: {profile.name}")
    st.caption(
        f"{profile.industry} · {profile.website} · generated {state['generated_at'].replace('T', ' ')[:16]}"
        f" · news from the last {state.get('news_days')} days"
    )
    if ss.get("saved_path"):
        path = ss.saved_path
        shown = path.relative_to(config.PROJECT_DIR) if path.is_relative_to(config.PROJECT_DIR) else path
        st.caption(f"Saved to `{shown}` (+ .md)")
    st.write(profile.description)

    if briefing:
        st.subheader("Executive summary")
        st.write(briefing.executive_summary)

    st.subheader("Comparison at a glance")
    rows = comparison_rows(reports)
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.info("No competitors could be analyzed.")

    if briefing:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Key takeaways")
            st.markdown("\n".join(f"- {t}" for t in briefing.key_takeaways))
        with col2:
            st.subheader("Pricing comparison")
            st.write(briefing.pricing_comparison)

    st.subheader("Competitor analysis cards")
    for tab, report in zip(st.tabs([f"{r.rank}. {r.competitor.name}" for r in reports]), reports):
        with tab:
            c = report.competitor
            st.markdown(f"#### {c.name}" + (f" · [{c.website}](https://{c.website})" if c.website else ""))
            st.caption(c.reason)
            if report.card:
                st.markdown(card_markdown(report.card))
            else:
                st.error(f"Analysis failed: {report.error}")
            with st.expander(f"Sources ({len(report.sources)})"):
                st.markdown("\n".join(f"- {u}" for u in report.sources))

    slug = slugify(profile.name)
    col1, col2, col3, _ = st.columns([1, 1, 1, 3])
    col1.download_button("Download Markdown", briefing_markdown(state), f"{slug}-competitors.md", "text/markdown")
    col2.download_button(
        "Download JSON", json.dumps(state_to_dict(state), indent=2), f"{slug}-competitors.json", "application/json"
    )
    if col3.button("New research"):
        reset()
        st.rerun()


with st.sidebar:
    st.header("Settings")
    num_competitors = st.slider(
        "Number of competitors", 1, config.MAX_COMPETITORS, config.NUM_COMPETITORS,
        help="Each competitor adds ~10k Groq tokens and ~40s of run time on the free tier.",
    )
    news_days = st.slider("News window (days)", 7, 365, config.NEWS_LOOKBACK_DAYS, step=1)
    review = st.toggle("Review competitors before research", value=True)
    ss.use_cache = st.toggle(
        f"Use cached results ({config.CACHE_TTL_HOURS}h)", value=True,
        help="Reuses Keenable searches and LLM outputs from the last few hours, so repeated research "
        "costs no Groq tokens. Turn off to force fresh research.",
    )
    st.caption(f"Model: `{config.GROQ_MODEL}`")

    st.header("Saved reports")
    saved = list_reports()
    if saved:
        choice = st.selectbox("Open a past briefing", saved, format_func=lambda r: r.label, index=None)
        if st.button("Open", disabled=choice is None) and choice:
            reset()
            ss.phase, ss.result, ss.saved_path = "done", load_report(choice.path), choice.path
            st.rerun()
    else:
        st.caption("Finished briefings are saved to `reports/` and listed here.")
    if st.button("Clear cache"):
        st.toast(f"Removed {cache.clear()} cached entries")

st.title("🔎 Marketing Research Agent")
st.write(
    "Discovers a company's top competitors and builds analysis cards covering pricing, "
    "core features, market positioning and recent news. Research only: it takes no actions."
)

if ss.phase == "input":
    with st.form("research"):
        col1, col2 = st.columns([2, 1])
        company = col1.text_input("Company", placeholder="e.g. Notion")
        website = col2.text_input("Website (optional, helps disambiguate)", placeholder="e.g. notion.com")
        submitted = st.form_submit_button("Run research", type="primary")
    if submitted:
        if not company.strip():
            st.warning("Enter a company name.")
        else:
            # A fresh thread + checkpointer per research run; they let a paused run resume after review
            ss.thread_id, ss.checkpointer = str(uuid.uuid4()), make_checkpointer()
            inputs = research_inputs(
                company.strip(), website.strip(), num_competitors=num_competitors, news_days=news_days, review=review
            )
            label = "Finding competitors..." if review else "Researching... (usually 1-3 minutes)"
            run_leg(label, inputs=inputs)
elif ss.phase == "review":
    show_review()
elif ss.phase == "done":
    show_results(ss.result)
