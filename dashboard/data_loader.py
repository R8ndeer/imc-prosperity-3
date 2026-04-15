from __future__ import annotations

"""Raw data loading layer for the Round 1 dashboard.

The Round 1 market-data CSVs are semicolon-delimited and intentionally loaded
with minimal semantic mutation here. Cleaning and canonical columns live in
`dashboard.preprocess`.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


PRICE_PATTERN = "prices_round_1_day_*.csv"
TRADE_PATTERN = "trades_round_1_day_*.csv"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "ROUND1"
DEFAULT_REPLAY_DIR = ROOT / "output" / "round1"


@dataclass(frozen=True)
class ReplayOutputs:
    fills: pd.DataFrame
    equity: pd.DataFrame
    summary: pd.DataFrame
    assumptions: list[str]


@dataclass(frozen=True)
class Round1RawBundle:
    prices: pd.DataFrame
    trades: pd.DataFrame
    replay: ReplayOutputs
    warnings: list[str]


def _extract_day_from_filename(path: Path) -> int:
    return int(path.stem.split("_")[-1])


def _read_semicolon_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";")


def _load_many_csvs(data_dir: Path, pattern: str, *, kind: str) -> tuple[pd.DataFrame, list[str]]:
    files = sorted(data_dir.glob(pattern))
    warnings: list[str] = []
    frames: list[pd.DataFrame] = []

    if not files:
        warnings.append(f"No {kind} files matched {data_dir / pattern}")
        return pd.DataFrame(), warnings

    for path in files:
        frame = _read_semicolon_csv(path)
        frame["source_file"] = path.name

        if "day" not in frame.columns:
            frame["day"] = _extract_day_from_filename(path)

        frames.append(frame)

    return pd.concat(frames, ignore_index=True), warnings


def load_prices(data_dir: Path = DEFAULT_DATA_DIR) -> tuple[pd.DataFrame, list[str]]:
    """Load raw Round 1 price snapshots.

    Expected raw schema includes `day`, `timestamp`, `product`, up to three bid
    and ask levels, `mid_price`, and `profit_and_loss`.
    """
    return _load_many_csvs(Path(data_dir), PRICE_PATTERN, kind="price")


def load_trades(data_dir: Path = DEFAULT_DATA_DIR) -> tuple[pd.DataFrame, list[str]]:
    """Load raw Round 1 historical market trades.

    Trade product identity is held in the `symbol` column, unlike price files
    where it is held in `product`.
    """
    return _load_many_csvs(Path(data_dir), TRADE_PATTERN, kind="trade")


def _read_optional_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _read_optional_assumptions(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        import json

        with open(path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        return list(loaded) if isinstance(loaded, list) else []
    except Exception:
        return []


def load_replay_outputs(replay_dir: Path = DEFAULT_REPLAY_DIR) -> ReplayOutputs:
    replay_dir = Path(replay_dir)
    return ReplayOutputs(
        fills=_read_optional_csv(replay_dir / "round1_fills.csv"),
        equity=_read_optional_csv(replay_dir / "round1_equity_history.csv"),
        summary=_read_optional_csv(replay_dir / "round1_summary.csv"),
        assumptions=_read_optional_assumptions(replay_dir / "round1_assumptions.json"),
    )


def load_round1_bundle(
    data_dir: Path = DEFAULT_DATA_DIR,
    replay_dir: Path = DEFAULT_REPLAY_DIR,
) -> Round1RawBundle:
    prices, price_warnings = load_prices(data_dir)
    trades, trade_warnings = load_trades(data_dir)
    replay = load_replay_outputs(replay_dir)
    return Round1RawBundle(
        prices=prices,
        trades=trades,
        replay=replay,
        warnings=[*price_warnings, *trade_warnings],
    )
