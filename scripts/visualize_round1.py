from __future__ import annotations

"""Secondary debug exporter for Round 1 dashboard figures.

The interactive dashboard is the primary visualization path:

    python -m dashboard.app

This script is intentionally small and reuses the dashboard data/plotting
layers to export standalone HTML figures for quick sharing or offline checks.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.plotting import build_market_figure, build_pnl_figure, build_position_figure
from dashboard.state import DEFAULT_CACHE_DIR, load_dashboard_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export dashboard figures as standalone debug HTML files.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output" / "round1_debug_figures")
    parser.add_argument("--cache-dir", type=str, default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--day", default="all")
    parser.add_argument("--max-snapshots", type=int, default=4000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = load_dashboard_data(cache_dir=args.cache_dir)

    products = sorted(data.snapshots["product"].dropna().unique())
    for product in products:
        market = build_market_figure(
            data.snapshots,
            data.trades,
            data.fills,
            product=product,
            day=args.day,
            indicator_overlays=["wall_mid"],
            max_snapshots=args.max_snapshots,
        )
        position = build_position_figure(data.equity, product=product, day=args.day, max_snapshots=args.max_snapshots)
        pnl = build_pnl_figure(data.equity, product=product, day=args.day, max_snapshots=args.max_snapshots)

        market.write_html(args.output_dir / f"{product.lower()}_market.html")
        position.write_html(args.output_dir / f"{product.lower()}_position.html")
        pnl.write_html(args.output_dir / f"{product.lower()}_pnl.html")
        print(f"Wrote debug figures for {product} to {args.output_dir}")


if __name__ == "__main__":
    main()
