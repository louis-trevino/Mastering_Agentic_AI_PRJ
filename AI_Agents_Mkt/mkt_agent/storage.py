"""Save finished briefings to the local reports/ folder (Markdown + JSON) and load them back."""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import config
from .report import briefing_markdown
from .schemas import Briefing, CompanyProfile, CompetitorReport


@dataclass
class SavedReport:
    path: Path  # the .json file
    company: str
    generated_at: str

    @property
    def label(self) -> str:
        return f"{self.company} · {self.generated_at.replace('T', ' ')[:16]}"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "report"


def state_to_dict(state: dict) -> dict:
    return {
        "generated_at": state.get("generated_at") or datetime.now().isoformat(timespec="seconds"),
        "settings": {
            "company": state.get("company", ""),
            "website": state.get("website", ""),
            "num_competitors": state.get("num_competitors"),
            "news_days": state.get("news_days"),
        },
        "profile": state["profile"].model_dump(),
        "briefing": state["briefing"].model_dump() if state.get("briefing") else None,
        "competitors": [r.model_dump() for r in state.get("reports", [])],
    }


def state_from_dict(data: dict) -> dict:
    return {
        **data.get("settings", {}),
        "generated_at": data["generated_at"],
        "profile": CompanyProfile.model_validate(data["profile"]),
        "briefing": Briefing.model_validate(data["briefing"]) if data.get("briefing") else None,
        "reports": [CompetitorReport.model_validate(r) for r in data["competitors"]],
    }


def save_report(state: dict, directory: Path | None = None) -> Path:
    """Write <timestamp>_<company>.json and .md; returns the JSON path."""
    directory = directory or config.REPORTS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    data = state_to_dict(state)
    stamp = data["generated_at"].replace(":", "").replace("-", "")
    stem = f"{stamp}_{slugify(state['profile'].name)}"
    json_path = directory / f"{stem}.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    (directory / f"{stem}.md").write_text(briefing_markdown(state), encoding="utf-8")
    return json_path


def list_reports(directory: Path | None = None) -> list[SavedReport]:
    """Saved reports, newest first. Unreadable files are skipped."""
    saved = []
    for path in (directory or config.REPORTS_DIR).glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            saved.append(SavedReport(path, data["profile"]["name"], data["generated_at"]))
        except (OSError, ValueError, KeyError):
            continue
    return sorted(saved, key=lambda r: r.generated_at, reverse=True)


def load_report(path: Path) -> dict:
    return state_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
