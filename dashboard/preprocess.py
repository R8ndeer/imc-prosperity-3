from __future__ import annotations

"""Canonical market-data preprocessing for dashboard-ready tables."""

from dataclasses import dataclass

import pandas as pd


PRICE_LEVELS = (1, 2, 3)
PRICE_COLUMNS = [
    "mid_price",
    "profit_and_loss",
    *[f"{side}_price_{level}" for side in ("bid", "ask") for level in PRICE_LEVELS],
    *[f"{side}_volume_{level}" for side in ("bid", "ask") for level in PRICE_LEVELS],
]


@dataclass(frozen=True)
class CanonicalBundle:
    snapshots: pd.DataFrame
    trades: pd.DataFrame
    fills: pd.DataFrame
    equity: pd.DataFrame
    warnings: list[str]


def _coerce_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    frame = frame.copy()
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _first_available(row: pd.Series, columns: list[str]) -> float:
    for column in columns:
        value = row.get(column)
        if pd.notna(value):
            return value
    return float("nan")


def _wall_price(row: pd.Series, side: str) -> float:
    values = [row.get(f"{side}_price_{level}") for level in PRICE_LEVELS]
    values = [float(value) for value in values if pd.notna(value)]
    if not values:
        return float("nan")
    return min(values) if side == "bid" else max(values)


def add_plot_index(frame: pd.DataFrame, product_column: str = "product") -> pd.DataFrame:
    """Add stable per-product/per-day snapshot indices."""
    if frame.empty:
        out = frame.copy()
        out["plot_index"] = pd.Series(dtype="int64")
        return out

    out = frame.sort_values(["product" if product_column == "product" else product_column, "day", "timestamp"]).copy()
    out["plot_index"] = out.groupby([product_column, "day"]).cumcount()
    return out.sort_values(["day", "timestamp", product_column]).reset_index(drop=True)


def clean_snapshots(raw_prices: pd.DataFrame) -> pd.DataFrame:
    """Build one canonical row per `(day, timestamp, product)` snapshot."""
    if raw_prices.empty:
        return pd.DataFrame()

    snapshots = raw_prices.copy()
    snapshots = _coerce_numeric(snapshots, ["day", "timestamp", *PRICE_COLUMNS])

    for side in ("bid", "ask"):
        for level in PRICE_LEVELS:
            price_col = f"{side}_price_{level}"
            volume_col = f"{side}_volume_{level}"
            if price_col in snapshots:
                snapshots.loc[snapshots[price_col] <= 0, price_col] = pd.NA
            if volume_col in snapshots:
                snapshots[volume_col] = snapshots[volume_col].abs()

    snapshots["best_bid"] = snapshots.apply(
        lambda row: _first_available(row, [f"bid_price_{level}" for level in PRICE_LEVELS]),
        axis=1,
    )
    snapshots["best_ask"] = snapshots.apply(
        lambda row: _first_available(row, [f"ask_price_{level}" for level in PRICE_LEVELS]),
        axis=1,
    )
    snapshots["wall_bid"] = snapshots.apply(lambda row: _wall_price(row, "bid"), axis=1)
    snapshots["wall_ask"] = snapshots.apply(lambda row: _wall_price(row, "ask"), axis=1)
    snapshots["wall_mid"] = (snapshots["wall_bid"] + snapshots["wall_ask"]) / 2
    snapshots.loc[snapshots["wall_bid"].isna() | snapshots["wall_ask"].isna(), "wall_mid"] = pd.NA

    snapshots["mid_price_clean"] = snapshots["mid_price"]
    snapshots.loc[snapshots["mid_price_clean"] <= 0, "mid_price_clean"] = pd.NA

    snapshots["spread"] = snapshots["best_ask"] - snapshots["best_bid"]
    snapshots.loc[snapshots["best_bid"].isna() | snapshots["best_ask"].isna(), "spread"] = pd.NA

    snapshots["top_bid_depth"] = snapshots["bid_volume_1"].fillna(0)
    snapshots["top_ask_depth"] = snapshots["ask_volume_1"].fillna(0)
    snapshots["book_missing"] = snapshots["best_bid"].isna() | snapshots["best_ask"].isna()

    keep_columns = [
        "day",
        "timestamp",
        "product",
        *[f"bid_price_{level}" for level in PRICE_LEVELS],
        *[f"bid_volume_{level}" for level in PRICE_LEVELS],
        *[f"ask_price_{level}" for level in PRICE_LEVELS],
        *[f"ask_volume_{level}" for level in PRICE_LEVELS],
        "mid_price",
        "profit_and_loss",
        "best_bid",
        "best_ask",
        "mid_price_clean",
        "wall_bid",
        "wall_ask",
        "wall_mid",
        "spread",
        "top_bid_depth",
        "top_ask_depth",
        "book_missing",
    ]
    keep_columns = [column for column in keep_columns if column in snapshots.columns]

    snapshots = snapshots[keep_columns].drop_duplicates(["day", "timestamp", "product"], keep="last")
    snapshots = add_plot_index(snapshots, "product")
    return snapshots


def clean_trades(raw_trades: pd.DataFrame) -> pd.DataFrame:
    if raw_trades.empty:
        return pd.DataFrame(columns=["day", "timestamp", "product", "buyer", "seller", "currency", "price", "quantity"])

    trades = raw_trades.copy()
    trades = trades.rename(columns={"symbol": "product"})
    trades = _coerce_numeric(trades, ["day", "timestamp", "price", "quantity"])
    trades.loc[trades["price"] <= 0, "price"] = pd.NA
    trades["quantity"] = trades["quantity"].abs()
    trades["trade_category"] = "historical"
    trades = trades.sort_values(["day", "timestamp", "product", "price"]).reset_index(drop=True)
    return trades


def clean_fills(raw_fills: pd.DataFrame) -> pd.DataFrame:
    if raw_fills.empty:
        return pd.DataFrame(columns=["day", "timestamp", "product", "side", "price", "quantity", "order_price", "liquidity"])

    fills = raw_fills.copy()
    fills = _coerce_numeric(fills, ["day", "timestamp", "price", "quantity", "order_price"])
    fills.loc[fills["price"] <= 0, "price"] = pd.NA
    fills["quantity"] = fills["quantity"].abs()
    fills["trade_category"] = "own_fill"
    return fills.sort_values(["day", "timestamp", "product", "price"]).reset_index(drop=True)


def clean_equity(raw_equity: pd.DataFrame) -> pd.DataFrame:
    if raw_equity.empty:
        return pd.DataFrame(columns=["day", "timestamp", "product", "position", "cash", "mid_price", "equity"])

    equity = raw_equity.copy()
    equity = _coerce_numeric(equity, ["day", "timestamp", "position", "cash", "mid_price", "equity"])
    equity.loc[equity["mid_price"] <= 0, "mid_price"] = pd.NA
    return equity.sort_values(["day", "timestamp", "product"]).reset_index(drop=True)


def build_canonical_bundle(raw_bundle) -> CanonicalBundle:
    snapshots = clean_snapshots(raw_bundle.prices)
    trades = clean_trades(raw_bundle.trades)
    fills = clean_fills(raw_bundle.replay.fills)
    equity = clean_equity(raw_bundle.replay.equity)
    return CanonicalBundle(
        snapshots=snapshots,
        trades=trades,
        fills=fills,
        equity=equity,
        warnings=list(raw_bundle.warnings),
    )


def validate_snapshots(snapshots: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    if snapshots.empty:
        return ["snapshots table is empty"]

    price_columns = ["best_bid", "best_ask", "mid_price_clean", "wall_mid"]
    for column in price_columns:
        if column in snapshots and (snapshots[column].dropna() == 0).any():
            errors.append(f"{column} contains zero price placeholders")

    for (day, product), group in snapshots.groupby(["day", "product"]):
        if not group["plot_index"].is_monotonic_increasing:
            errors.append(f"plot_index is not monotonic for day={day}, product={product}")
        if group["plot_index"].duplicated().any():
            errors.append(f"plot_index has duplicates for day={day}, product={product}")

    duplicates = snapshots.duplicated(["day", "timestamp", "product"]).sum()
    if duplicates:
        errors.append(f"snapshots has {duplicates} duplicate day/timestamp/product rows")

    return errors
