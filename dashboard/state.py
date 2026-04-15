from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "ROUND1"
DEFAULT_REPLAY_DIR = ROOT / "output" / "round1"
DEFAULT_CACHE_DIR = ROOT / "output" / "dashboard_cache"

