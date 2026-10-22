"""Streamlit UI flow tests (AppTest), running against the fake Keenable + fake LLM."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from mkt_agent import config

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def app(fake_keenable, fake_llm) -> AppTest:
    return AppTest.from_file(APP, default_timeout=60).run()


def start_research(at: AppTest, company="Trello", website="trello.com") -> None:
    at.text_input[0].input(company)
    at.text_input[1].input(website)
    at.button[0].click().run()


def test_empty_company_shows_warning(app):
    app.button[0].click().run()
    assert [w.value for w in app.warning] == ["Enter a company name."]
    assert app.session_state["phase"] == "input"


def test_review_flow_then_results_and_auto_save(app):
    app.sidebar.slider[0].set_value(2)
    start_research(app)

    assert not app.exception
    assert app.session_state["phase"] == "review"
    assert [c["name"] for c in app.session_state["proposal"]["competitors"]] == ["Asana", "Monday.com"]

    [approve] = [b for b in app.button if b.label == "Approve & research"]
    approve.click().run()

    assert not app.exception
    assert app.session_state["phase"] == "done"
    assert app.header[0].value == "Competitive Briefing: Trello"
    assert [t.label for t in app.tabs] == ["1. Asana", "2. Monday.com"]
    assert "Comparison at a glance" in [s.value for s in app.subheader]
    assert len(app.dataframe) == 1

    saved = list(config.REPORTS_DIR.glob("*.json"))
    assert len(saved) == 1 and saved[0].with_suffix(".md").exists()


def test_without_review_goes_straight_to_results(app):
    app.sidebar.toggle[0].set_value(False)
    app.sidebar.slider[0].set_value(1)
    start_research(app)

    assert not app.exception
    assert app.session_state["phase"] == "done"
    assert [t.label for t in app.tabs] == ["1. Asana"]


def test_start_over_from_review(app):
    start_research(app)
    [start_over] = [b for b in app.button if b.label == "Start over"]
    start_over.click().run()
    assert app.session_state["phase"] == "input"


def test_open_saved_report_from_sidebar(app):
    app.sidebar.toggle[0].set_value(False)
    start_research(app)
    [new] = [b for b in app.button if b.label == "New research"]
    new.click().run()
    assert app.session_state["phase"] == "input"

    app.sidebar.selectbox[0].select_index(0).run()  # "Open" is enabled once a report is selected
    [open_button] = [b for b in app.sidebar.button if b.label == "Open"]
    open_button.click().run()

    assert not app.exception
    assert app.session_state["phase"] == "done"
    assert app.header[0].value == "Competitive Briefing: Trello"
