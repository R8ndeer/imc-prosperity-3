from __future__ import annotations

from pathlib import Path

import pandas as pd


TABLES = ("snapshots", "trades", "fills", "equity", "logs")


def parquet_available() -> bool:
    try:
        import pyarrow  # noqa: F401

        return True
    except Exception:
        return False


def cache_path(cache_dir: Path, table: str) -> Path:
    suffix = "parquet" if parquet_available() else "csv"
    return Path(cache_dir) / f"{table}.{suffix}"


def write_cache(cache_dir: Path, tables: dict[str, pd.DataFrame]) -> None:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    use_parquet = parquet_available()
    for table, frame in tables.items():
        if table not in TABLES:
            continue
        path = cache_dir / f"{table}.{'parquet' if use_parquet else 'csv'}"
        if use_parquet:
            frame.to_parquet(path, index=False)
        else:
            frame.to_csv(path, index=False)


def read_cache(cache_dir: Path) -> dict[str, pd.DataFrame] | None:
    cache_dir = Path(cache_dir)
    paths = {table: cache_path(cache_dir, table) for table in TABLES}
    if not all(path.exists() for path in paths.values()):
        return None

    use_parquet = parquet_available()
    if use_parquet:
        return {table: pd.read_parquet(path) for table, path in paths.items()}
    return {table: pd.read_csv(path) for table, path in paths.items()}
