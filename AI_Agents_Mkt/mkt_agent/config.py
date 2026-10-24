"""Central configuration, loaded from the project's .env file."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

KEENABLE_API_KEY = os.getenv("KEENABLE_API_KEY", "")
KEENABLE_MCP_URL = "https://api.keenable.ai/mcp"
KEENABLE_MAX_RPS = 8  # the account limit is 10 requests/second; keep some headroom

# Per-run defaults (adjustable in the UI / CLI)
NUM_COMPETITORS = 3
MAX_COMPETITORS = 5  # each competitor costs ~10k Groq tokens
NEWS_LOOKBACK_DAYS = 90

SEARCH_MAX_RESULTS = 5
SNIPPET_MAX_LENGTH = 800

# Disk cache for Keenable results and LLM outputs (saves quota on repeated research)
CACHE_DIR = PROJECT_DIR / ".cache" / "mkt_agent"
CACHE_TTL_HOURS = 6

# Saved briefings (Markdown + JSON per run)
REPORTS_DIR = PROJECT_DIR / "reports"


def check_config() -> None:
    missing = [name for name, value in (("GROQ_API_KEY", GROQ_API_KEY), ("KEENABLE_API_KEY", KEENABLE_API_KEY)) if not value]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)} (add them to .env)")
