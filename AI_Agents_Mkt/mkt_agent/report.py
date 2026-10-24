"""Render a finished research state as a Markdown briefing."""

from datetime import datetime

from .schemas import CompetitorCard, CompetitorReport

COMPARISON_COLUMNS = ["Competitor", "Starting price", "Free plan", "Target segment", "Key differentiator", "Latest news"]


def _cell(text: str) -> str:
    """Make text safe for a Markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


def generated_date(state: dict) -> str:
    return state.get("generated_at", datetime.now().isoformat(timespec="seconds"))[:10]


def comparison_rows(reports: list[CompetitorReport]) -> list[dict[str, str]]:
    """One row per analyzed competitor for the side-by-side comparison (no LLM call)."""
    rows = []
    for r in reports:
        if not r.card:
            continue
        card, pos = r.card, r.card.market_positioning
        latest = card.recent_news[0] if card.recent_news else None
        values = [
            r.competitor.name,
            card.starting_price,
            card.free_plan,
            pos.target_segment,
            pos.differentiators[0] if pos.differentiators else "",
            f"{latest.date or 'n/a'}: {latest.headline}" if latest else "None found",
        ]
        rows.append(dict(zip(COMPARISON_COLUMNS, values)))
    return rows


def comparison_markdown(reports: list[CompetitorReport]) -> str:
    rows = comparison_rows(reports)
    if not rows:
        return "_No competitors could be analyzed._"
    lines = ["| " + " | ".join(COMPARISON_COLUMNS) + " |", "|" + "---|" * len(COMPARISON_COLUMNS)]
    lines += ["| " + " | ".join(_cell(row[c]) for c in COMPARISON_COLUMNS) + " |" for row in rows]
    return "\n".join(lines)


def card_markdown(card: CompetitorCard) -> str:
    lines = [
        card.overview,
        "",
        "**Pricing**",
        "",
        f"Starting price: **{card.starting_price}** · Free plan: **{card.free_plan}**",
        "",
    ]
    if card.pricing:
        lines += ["| Plan | Price | Details |", "|---|---|---|"]
        lines += [f"| {_cell(t.plan)} | {_cell(t.price)} | {_cell(t.details)} |" for t in card.pricing]
    if card.pricing_notes:
        lines += ["", f"_{card.pricing_notes}_"]

    lines += ["", "**Core features**", ""] + [f"- {f}" for f in card.core_features]

    pos = card.market_positioning
    lines += [
        "",
        "**Market positioning**",
        "",
        f"- **Target segment:** {pos.target_segment}",
        f"- **Value proposition:** {pos.value_proposition}",
    ]
    lines += [f"- **Differentiator:** {d}" for d in pos.differentiators]

    lines += ["", "**Recent news**", ""]
    lines += [f"- {n.date or 'n/a'} - [{n.headline}]({n.url}): {n.summary}" for n in card.recent_news] or [
        "- No recent news found."
    ]

    lines += ["", "**Strengths**", ""] + [f"- {s}" for s in card.strengths]
    lines += ["", "**Weaknesses**", ""] + [f"- {w}" for w in card.weaknesses]
    return "\n".join(lines)


def report_markdown(report: CompetitorReport) -> str:
    c = report.competitor
    head = f"## {report.rank}. {c.name}" + (f" ({c.website})" if c.website else "")
    body = card_markdown(report.card) if report.card else f"Analysis failed: {report.error}"
    sources = "\n".join(f"- {u}" for u in report.sources)
    return f"{head}\n\n_{c.reason}_\n\n{body}\n\n<details><summary>Sources</summary>\n\n{sources}\n\n</details>"


def briefing_markdown(state: dict) -> str:
    profile, briefing = state["profile"], state.get("briefing")
    reports = state.get("reports", [])
    parts = [
        f"# Competitive Briefing: {profile.name}",
        f"_{profile.industry} | {profile.website} | generated {generated_date(state)}"
        f" | news from the last {state.get('news_days', '?')} days_",
        profile.description,
    ]
    if briefing:
        parts += [
            "## Executive summary",
            briefing.executive_summary,
            "## Key takeaways",
            "\n".join(f"- {t}" for t in briefing.key_takeaways),
        ]
    parts += ["## Comparison at a glance", comparison_markdown(reports)]
    if briefing:
        parts += ["## Pricing comparison", briefing.pricing_comparison]
    parts += [report_markdown(r) for r in reports]
    return "\n\n".join(parts)
