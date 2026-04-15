from __future__ import annotations

"""Adapters for aligning replay outputs to market snapshots."""

from dataclasses import dataclass

import pandas as pd


JOIN_KEYS = ["day", "timestamp", "product"]


@dataclass(frozen=True)
class ReplayTables:
    fills: pd.DataFrame
    equity: pd.DataFrame
    warnings: list[str]


def _snapshot_lookup(snapshots: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "day",
        "timestamp",
        "product",
        "plot_index",
        "mid_price_clean",
        "best_bid",
        "best_ask",
        "wall_mid",
        "spread",
        "book_missing",
    ]
    columns = [column for column in columns if column in snapshots.columns]
    lookup = snapshots[columns].drop_duplicates(JOIN_KEYS)
    return lookup


def align_fills_to_snapshots(fills: pd.DataFrame, snapshots: pd.DataFrame) -> pd.DataFrame:
    if fills.empty:
        out = fills.copy()
        for column in ["plot_index", "mid_price_clean", "best_bid", "best_ask", "wall_mid", "spread", "book_missing"]:
            if column not in out:
                out[column] = pd.Series(dtype="float64")
        return out

    before_rows = len(fills)
    aligned = fills.merge(_snapshot_lookup(snapshots), on=JOIN_KEYS, how="left", validate="many_to_one")
    if len(aligned) != before_rows:
        raise ValueError("fill-to-snapshot join changed row count")
    return aligned


def align_equity_to_snapshots(equity: pd.DataFrame, snapshots: pd.DataFrame) -> pd.DataFrame:
    if equity.empty:
        out = equity.copy()
        for column in ["plot_index", "mid_price_clean", "best_bid", "best_ask", "wall_mid", "spread", "book_missing"]:
            if column not in out:
                out[column] = pd.Series(dtype="float64")
        return out

    before_rows = len(equity)
    aligned = equity.merge(_snapshot_lookup(snapshots), on=JOIN_KEYS, how="left", validate="one_to_one")
    if len(aligned) != before_rows:
        raise ValueError("equity-to-snapshot join changed row count")
    return aligned


def build_replay_tables(canonical_bundle) -> ReplayTables:
    warnings: list[str] = []
    fills = align_fills_to_snapshots(canonical_bundle.fills, canonical_bundle.snapshots)
    equity = align_equity_to_snapshots(canonical_bundle.equity, canonical_bundle.snapshots)

    if not fills.empty and fills["plot_index"].isna().any():
        warnings.append("Some fills could not be aligned to market snapshots")
    if not equity.empty and equity["plot_index"].isna().any():
        warnings.append("Some equity rows could not be aligned to market snapshots")

    return ReplayTables(fills=fills, equity=equity, warnings=warnings)


def details_for_timestamp(
    snapshots: pd.DataFrame,
    trades: pd.DataFrame,
    fills: pd.DataFrame,
    equity: pd.DataFrame,
    logs: pd.DataFrame | None = None,
    *,
    day: int,
    timestamp: int,
    product: str,
) -> dict[str, object]:
    key_mask = (
        (snapshots["day"] == day)
        & (snapshots["timestamp"] == timestamp)
        & (snapshots["product"] == product)
    )
    snapshot_rows = snapshots.loc[key_mask]
    snapshot = snapshot_rows.iloc[0].to_dict() if not snapshot_rows.empty else {}

    trade_rows = trades[
        (trades["day"] == day)
        & (trades["timestamp"] == timestamp)
        & (trades["product"] == product)
    ]
    fill_rows = fills[
        (fills["day"] == day)
        & (fills["timestamp"] == timestamp)
        & (fills["product"] == product)
    ]
    equity_rows = equity[
        (equity["day"] == day)
        & (equity["timestamp"] == timestamp)
        & (equity["product"] == product)
    ]
    if logs is None or logs.empty or "timestamp" not in logs:
        log_rows = pd.DataFrame()
    else:
        log_rows = logs[
            (logs["timestamp"] == timestamp)
            & ((logs["product"] == product) | (logs["product"].isna()))
        ]

    return {
        "snapshot": snapshot,
        "trades": trade_rows.to_dict("records"),
        "fills": fill_rows.to_dict("records"),
        "equity": equity_rows.iloc[0].to_dict() if not equity_rows.empty else {},
        "logs": log_rows.to_dict("records"),
    }
