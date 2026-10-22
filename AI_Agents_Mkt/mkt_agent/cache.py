"""Small JSON disk cache with a time-to-live, for Keenable results and LLM outputs.

Caching is best effort: any cache read/write problem falls back to a live call.
It can be switched off per run with `disabled()`, e.g. to force fresh research.
"""

import hashlib
import json
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from . import config

_enabled: ContextVar[bool] = ContextVar("mkt_agent_cache_enabled", default=True)


@contextmanager
def enabled(flag: bool = True):
    """Turn the cache on/off for code run inside this block (including tasks it starts)."""
    token = _enabled.set(flag)
    try:
        yield
    finally:
        _enabled.reset(token)


def make_key(*parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def _path(namespace: str, key: str):
    return config.CACHE_DIR / namespace / f"{key}.json"


def get(namespace: str, key: str) -> Any | None:
    if not _enabled.get():
        return None
    try:
        entry = json.loads(_path(namespace, key).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if time.time() - entry["created"] > config.CACHE_TTL_HOURS * 3600:
        return None
    return entry["value"]


def put(namespace: str, key: str, value: Any) -> None:
    if not _enabled.get():
        return
    path = _path(namespace, key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"created": time.time(), "value": value}), encoding="utf-8")
    except OSError:
        pass


def clear() -> int:
    """Delete all cache entries; returns how many were removed."""
    removed = 0
    for path in config.CACHE_DIR.glob("*/*.json"):
        path.unlink(missing_ok=True)
        removed += 1
    return removed
