from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from dashboard.data_loader import load_round1_bundle
from dashboard.log_parser import load_logs
from dashboard.preprocess import build_canonical_bundle
from dashboard.replay_adapter import build_replay_tables


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "ROUND1"
DEFAULT_REPLAY_DIR = ROOT / "output" / "round1"
DEFAULT_CACHE_DIR = ROOT / "output" / "dashboard_cache"
DEFAULT_LOG_DIR = ROOT / "output" / "round1" / "logs"


@dataclass(frozen=True)
class DashboardData:
    snapshots: pd.DataFrame
    trades: pd.DataFrame
    fills: pd.DataFrame
    equity: pd.DataFrame
    logs: pd.DataFrame
    warnings: list[str]


@lru_cache(maxsize=4)
def load_dashboard_data(
    data_dir: str = str(DEFAULT_DATA_DIR),
    replay_dir: str = str(DEFAULT_REPLAY_DIR),
    log_dir: str = str(DEFAULT_LOG_DIR),
) -> DashboardData:
    raw = load_round1_bundle(Path(data_dir), Path(replay_dir))
    canonical = build_canonical_bundle(raw)
    replay = build_replay_tables(canonical)

    trades = canonical.trades.merge(
        canonical.snapshots[["day", "timestamp", "product", "plot_index", "mid_price_clean", "wall_mid"]],
        on=["day", "timestamp", "product"],
        how="left",
        validate="many_to_one",
    )

    return DashboardData(
        snapshots=canonical.snapshots,
        trades=trades,
        fills=replay.fills,
        equity=replay.equity,
        logs=load_logs(Path(log_dir)),
        warnings=[*canonical.warnings, *replay.warnings],
    )


def product_options(data: DashboardData) -> list[dict[str, str]]:
    return [{"label": product, "value": product} for product in sorted(data.snapshots["product"].dropna().unique())]


def day_options(data: DashboardData) -> list[dict[str, str | int]]:
    days = sorted(data.snapshots["day"].dropna().astype(int).unique())
    return [{"label": "All days", "value": "all"}, *[{"label": f"Day {day}", "value": int(day)} for day in days]]
