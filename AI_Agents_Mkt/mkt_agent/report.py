"""Render a finished research state as a Markdown briefing."""

from datetime import date

from .schemas import CompetitorCard, CompetitorReport


def card_markdown(card: CompetitorCard) -> str:
    lines = [card.overview, "", "**Pricing**", ""]
    if card.pricing:
        lines += ["| Plan | Price | Details |", "|---|---|---|"]
        lines += [f"| {t.plan} | {t.price} | {t.details} |" for t in card.pricing]
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
    parts = [
        f"# Competitive Briefing: {profile.name}",
        f"_{profile.industry} | {profile.website} | generated {date.today().isoformat()}"
        f" | news from the last {state.get('news_days', '?')} days_",
        profile.description,
    ]
    if briefing:
        parts += [
            "## Executive summary",
            briefing.executive_summary,
            "## Key takeaways",
            "\n".join(f"- {t}" for t in briefing.key_takeaways),
            "## Pricing comparison",
            briefing.pricing_comparison,
        ]
    parts += [report_markdown(r) for r in state.get("reports", [])]
    return "\n\n".join(parts)
