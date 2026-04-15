from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from round1_baseline_trader import Trader
from round1_data_utils import format_summary_block, load_round1_data, run_round1_replay


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay this year's Round 1 baseline on historical CSV data.")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "ROUND1", help="Directory containing Round 1 prices/trades CSVs.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output" / "round1", help="Directory for summary artifacts.")
    parser.add_argument(
        "--passive-fill-mode",
        choices=["none", "trade_touch"],
        default="trade_touch",
        help="Passive-fill heuristic used during replay.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    prices, trades, warnings = load_round1_data(args.data_dir)
    replay = run_round1_replay(Trader, prices, trades, passive_fill_mode=args.passive_fill_mode)

    fills: pd.DataFrame = replay["fills"]
    equity_history: pd.DataFrame = replay["equity_history"]
    summary: pd.DataFrame = replay["summary"]

    fills.to_csv(args.output_dir / "round1_fills.csv", index=False)
    equity_history.to_csv(args.output_dir / "round1_equity_history.csv", index=False)
    summary.to_csv(args.output_dir / "round1_summary.csv", index=False)

    with open(args.output_dir / "round1_assumptions.json", "w", encoding="utf-8") as handle:
        json.dump(replay["assumptions"], handle, indent=2)

    report = format_summary_block(summary, warnings, args.passive_fill_mode)
    print(report)


if __name__ == "__main__":
    main()
