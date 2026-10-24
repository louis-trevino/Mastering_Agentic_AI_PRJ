"""Report rendering (comparison table, Markdown) and saving/loading briefings."""

from conftest import make_card

from mkt_agent import briefing_markdown
from mkt_agent.report import comparison_markdown, comparison_rows
from mkt_agent.schemas import Briefing, CompanyProfile, Competitor, CompetitorReport
from mkt_agent.storage import list_reports, load_report, save_report


def make_state(**overrides) -> dict:
    state = {
        "company": "Trello",
        "website": "trello.com",
        "num_competitors": 2,
        "news_days": 30,
        "generated_at": "2026-10-22T15:30:00",
        "profile": CompanyProfile(
            name="Trello", website="trello.com", industry="PM software", description="Boards.", main_products=["Trello"]
        ),
        "briefing": Briefing(executive_summary="Summary.", key_takeaways=["A", "B"], pricing_comparison="Pricing."),
        "reports": [
            CompetitorReport(
                rank=1,
                competitor=Competitor(name="Asana", website="asana.com", reason="Rival"),
                card=make_card("Asana", starting_price="$10 | billed yearly"),
                sources=["https://asana.com/pricing"],
            ),
            CompetitorReport(
                rank=2,
                competitor=Competitor(name="Wrike", website="", reason="Rival"),
                error="RuntimeError: boom",
            ),
        ],
    }
    state.update(overrides)
    return state


def test_comparison_rows_skip_failed_competitors():
    rows = comparison_rows(make_state()["reports"])
    assert rows == [
        {
            "Competitor": "Asana",
            "Starting price": "$10 | billed yearly",
            "Free plan": "Yes",
            "Target segment": "SMB teams",
            "Key differentiator": "Asana differentiator",
            "Latest news": "2026-10-01: Asana launches AI",
        }
    ]


def test_comparison_markdown_escapes_pipes():
    table = comparison_markdown(make_state()["reports"])
    assert "$10 \\| billed yearly" in table
    assert table.splitlines()[0].startswith("| Competitor | Starting price |")


def test_briefing_markdown_sections():
    md = briefing_markdown(make_state())
    for heading in ("# Competitive Briefing: Trello", "## Executive summary", "## Comparison at a glance",
                    "## Pricing comparison", "## 1. Asana (asana.com)", "## 2. Wrike"):
        assert heading in md
    assert "generated 2026-10-22" in md and "news from the last 30 days" in md
    assert "Analysis failed: RuntimeError: boom" in md


def test_save_list_and_load_roundtrip(tmp_path):
    state = make_state()
    path = save_report(state, tmp_path)

    assert path.name == "20261022T153000_trello.json"
    assert path.with_suffix(".md").read_text(encoding="utf-8") == briefing_markdown(state)

    [saved] = list_reports(tmp_path)
    assert (saved.company, saved.path) == ("Trello", path)

    loaded = load_report(path)
    for key in ("profile", "briefing", "reports", "news_days", "num_competitors", "generated_at", "website"):
        assert loaded[key] == state[key], key


def test_list_reports_newest_first_and_skips_bad_files(tmp_path):
    save_report(make_state(generated_at="2026-10-01T09:00:00"), tmp_path)
    save_report(make_state(generated_at="2026-10-20T09:00:00"), tmp_path)
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")

    assert [r.generated_at for r in list_reports(tmp_path)] == ["2026-10-20T09:00:00", "2026-10-01T09:00:00"]


def test_list_reports_when_folder_missing(tmp_path):
    assert list_reports(tmp_path / "nope") == []
