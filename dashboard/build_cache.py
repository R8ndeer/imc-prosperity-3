from __future__ import annotations

import argparse
from pathlib import Path

from dashboard.cache import write_cache
from dashboard.state import DEFAULT_CACHE_DIR, load_dashboard_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build processed dashboard cache files.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--data-dir", type=str, default=None)
    parser.add_argument("--replay-dir", type=str, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    kwargs = {}
    if args.data_dir is not None:
        kwargs["data_dir"] = args.data_dir
    if args.replay_dir is not None:
        kwargs["replay_dir"] = args.replay_dir

    data = load_dashboard_data(**kwargs)
    write_cache(
        args.cache_dir,
        {
            "snapshots": data.snapshots,
            "trades": data.trades,
            "fills": data.fills,
            "equity": data.equity,
            "logs": data.logs,
        },
    )
    print(f"Wrote dashboard cache to {args.cache_dir}")


if __name__ == "__main__":
    main()
