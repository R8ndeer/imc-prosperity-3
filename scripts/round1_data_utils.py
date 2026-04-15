from __future__ import annotations

import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datamodel import Observations, Order, OrderDepth, Trade, TradingState
from round1_baseline_trader import POSITION_LIMITS, ROUND1_PRODUCTS, get_book_walls


PRICE_LEVELS = (1, 2, 3)
REPLAY_ASSUMPTIONS = [
    "Strategy observes one visible book snapshot per product at each timestamp.",
    "Aggressive orders fill immediately against visible quoted depth level-by-level.",
    "Passive fills are not exact simulator emulation; they use a conservative heuristic.",
    "Passive fill mode 'none' assumes no passive fills.",
    "Passive fill mode 'trade_touch' fills passive orders only when historical trade prices reach the order price, capped by remaining historical traded quantity at that timestamp.",
    "Historical market trades are used for diagnostics and optional passive-fill heuristics, not as proof that our resting order definitely filled.",
    "PnL is marked to the snapshot mid_price when available; otherwise the latest known mid is carried forward.",
]


@dataclass
class ReplayFill:
    day: int
    timestamp: int
    product: str
    side: str
    price: float
    quantity: int
    order_price: int
    liquidity: str


def _read_semicolon_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";")


def _add_day_from_filename(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
    day = int(path.stem.split("_")[-1])
    frame = frame.copy()
    frame["day"] = day
    return frame


def _coerce_numeric_columns(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    frame = frame.copy()
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def enrich_price_features(prices: pd.DataFrame) -> pd.DataFrame:
    prices = prices.copy()
    prices["best_bid"] = prices[[f"bid_price_{level}" for level in PRICE_LEVELS]].bfill(axis=1).iloc[:, 0]
    prices["best_ask"] = prices[[f"ask_price_{level}" for level in PRICE_LEVELS]].bfill(axis=1).iloc[:, 0]
    prices["bid_depth_1"] = prices["bid_volume_1"].fillna(0)
    prices["ask_depth_1"] = prices["ask_volume_1"].fillna(0)
    prices["spread"] = prices["best_ask"] - prices["best_bid"]

    wall_mids = []
    for _, row in prices.iterrows():
        bid_prices = [int(row[f"bid_price_{level}"]) for level in PRICE_LEVELS if pd.notna(row[f"bid_price_{level}"])]
        ask_prices = [int(row[f"ask_price_{level}"]) for level in PRICE_LEVELS if pd.notna(row[f"ask_price_{level}"])]
        bid_wall = min(bid_prices) if bid_prices else None
        ask_wall = max(ask_prices) if ask_prices else None
        wall_mids.append((bid_wall + ask_wall) / 2 if bid_wall is not None and ask_wall is not None else None)
    prices["wall_mid"] = wall_mids
    return prices


def load_round1_prices(data_dir: Path) -> tuple[pd.DataFrame, list[str]]:
    files = sorted(data_dir.glob("prices_round_1_day_*.csv"))
    warnings: list[str] = []
    frames = []

    numeric_columns = [
        "day",
        "timestamp",
        "mid_price",
        "profit_and_loss",
        *[f"{side}_{field}_{level}" for side in ("bid", "ask") for field in ("price", "volume") for level in PRICE_LEVELS],
    ]

    for path in files:
        frame = _read_semicolon_csv(path)
        frame = _coerce_numeric_columns(frame, numeric_columns)
        frame["source_file"] = path.name
        frames.append(frame)

        rows_without_bids = int(frame[[f"bid_price_{level}" for level in PRICE_LEVELS]].isna().all(axis=1).sum())
        rows_without_asks = int(frame[[f"ask_price_{level}" for level in PRICE_LEVELS]].isna().all(axis=1).sum())
        if rows_without_bids:
            warnings.append(f"{path.name}: {rows_without_bids} rows have no visible bid levels")
        if rows_without_asks:
            warnings.append(f"{path.name}: {rows_without_asks} rows have no visible ask levels")

    prices = pd.concat(frames, ignore_index=True)
    prices = enrich_price_features(prices)
    prices = prices.sort_values(["day", "timestamp", "product"]).reset_index(drop=True)
    return prices, warnings


def load_round1_trades(data_dir: Path) -> tuple[pd.DataFrame, list[str]]:
    files = sorted(data_dir.glob("trades_round_1_day_*.csv"))
    warnings: list[str] = []
    frames = []

    for path in files:
        frame = _read_semicolon_csv(path)
        frame = _add_day_from_filename(frame, path)
        frame = _coerce_numeric_columns(frame, ["day", "timestamp", "price", "quantity"])
        frame["source_file"] = path.name
        frames.append(frame)

        malformed_rows = int(frame["symbol"].isna().sum() + frame["timestamp"].isna().sum())
        if malformed_rows:
            warnings.append(f"{path.name}: {malformed_rows} rows are missing symbol or timestamp")

    trades = pd.concat(frames, ignore_index=True)
    trades["buyer"] = trades["buyer"].replace({"": None})
    trades["seller"] = trades["seller"].replace({"": None})
    trades = trades.sort_values(["day", "timestamp", "symbol", "price"]).reset_index(drop=True)
    return trades, warnings


def load_round1_data(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    prices, price_warnings = load_round1_prices(data_dir)
    trades, trade_warnings = load_round1_trades(data_dir)
    return prices, trades, [*price_warnings, *trade_warnings]


def row_to_order_depth(row: pd.Series) -> OrderDepth:
    buy_orders: dict[int, int] = {}
    sell_orders: dict[int, int] = {}

    for level in PRICE_LEVELS:
        bid_price = row.get(f"bid_price_{level}")
        bid_volume = row.get(f"bid_volume_{level}")
        if pd.notna(bid_price) and pd.notna(bid_volume):
            buy_orders[int(bid_price)] = int(abs(bid_volume))

        ask_price = row.get(f"ask_price_{level}")
        ask_volume = row.get(f"ask_volume_{level}")
        if pd.notna(ask_price) and pd.notna(ask_volume):
            sell_orders[int(ask_price)] = -int(abs(ask_volume))

    return OrderDepth(buy_orders=buy_orders, sell_orders=sell_orders)


def extract_visible_levels(row: pd.Series, side: str) -> list[list[int]]:
    levels = []
    for level in PRICE_LEVELS:
        price = row.get(f"{side}_price_{level}")
        volume = row.get(f"{side}_volume_{level}")
        if pd.notna(price) and pd.notna(volume):
            levels.append([int(price), int(abs(volume))])

    if side == "bid":
        levels.sort(key=lambda item: item[0], reverse=True)
    else:
        levels.sort(key=lambda item: item[0])
    return levels


def build_market_trades(trades_slice: pd.DataFrame) -> dict[str, list[Trade]]:
    market_trades: dict[str, list[Trade]] = {}
    for product, product_frame in trades_slice.groupby("symbol"):
        market_trades[product] = [
            Trade(
                symbol=product,
                price=int(row.price),
                quantity=int(row.quantity),
                buyer=row.buyer if pd.notna(row.buyer) else None,
                seller=row.seller if pd.notna(row.seller) else None,
                timestamp=int(row.timestamp),
            )
            for row in product_frame.itertuples(index=False)
        ]
    return market_trades


def _consume_aggressive_buy(
    remaining: int,
    asks: list[list[int]],
    limit_price: int,
    fill_sink: list[ReplayFill],
    *,
    day: int,
    timestamp: int,
    product: str,
) -> int:
    for level in asks:
        price, visible_qty = level
        if remaining <= 0 or visible_qty <= 0 or price > limit_price:
            continue
        fill_qty = min(remaining, visible_qty)
        if fill_qty <= 0:
            continue
        fill_sink.append(ReplayFill(day, timestamp, product, "BUY", price, fill_qty, limit_price, "aggressive"))
        level[1] -= fill_qty
        remaining -= fill_qty
        if remaining <= 0:
            break
    return remaining


def _consume_aggressive_sell(
    remaining: int,
    bids: list[list[int]],
    limit_price: int,
    fill_sink: list[ReplayFill],
    *,
    day: int,
    timestamp: int,
    product: str,
) -> int:
    for level in bids:
        price, visible_qty = level
        if remaining <= 0 or visible_qty <= 0 or price < limit_price:
            continue
        fill_qty = min(remaining, visible_qty)
        if fill_qty <= 0:
            continue
        fill_sink.append(ReplayFill(day, timestamp, product, "SELL", price, fill_qty, limit_price, "aggressive"))
        level[1] -= fill_qty
        remaining -= fill_qty
        if remaining <= 0:
            break
    return remaining


def _consume_passive_trade_touch(
    remaining: int,
    side: str,
    limit_price: int,
    historical_prints: list[dict[str, float]],
    fill_sink: list[ReplayFill],
    *,
    day: int,
    timestamp: int,
    product: str,
) -> int:
    for trade in historical_prints:
        trade_price = int(trade["price"])
        trade_qty = int(trade["remaining_qty"])
        if remaining <= 0 or trade_qty <= 0:
            continue

        eligible = trade_price <= limit_price if side == "BUY" else trade_price >= limit_price
        if not eligible:
            continue

        fill_qty = min(remaining, trade_qty)
        fill_sink.append(ReplayFill(day, timestamp, product, side, limit_price, fill_qty, limit_price, "passive_trade_touch"))
        trade["remaining_qty"] -= fill_qty
        remaining -= fill_qty
        if remaining <= 0:
            break
    return remaining


def simulate_product_orders(
    day: int,
    timestamp: int,
    product: str,
    orders: list[Order],
    snapshot_row: pd.Series,
    trades_slice: pd.DataFrame,
    passive_fill_mode: str = "trade_touch",
) -> list[ReplayFill]:
    bids = extract_visible_levels(snapshot_row, "bid")
    asks = extract_visible_levels(snapshot_row, "ask")
    prints_budget = [
        {"price": float(row.price), "remaining_qty": int(abs(row.quantity))}
        for row in trades_slice.itertuples(index=False)
    ]
    fills: list[ReplayFill] = []

    for order in orders:
        remaining = abs(int(order.quantity))
        if remaining <= 0:
            continue

        if order.quantity > 0:
            remaining = _consume_aggressive_buy(
                remaining,
                asks,
                int(order.price),
                fills,
                day=day,
                timestamp=timestamp,
                product=product,
            )
            if remaining > 0 and passive_fill_mode == "trade_touch":
                _consume_passive_trade_touch(
                    remaining,
                    "BUY",
                    int(order.price),
                    prints_budget,
                    fills,
                    day=day,
                    timestamp=timestamp,
                    product=product,
                )
        else:
            remaining = _consume_aggressive_sell(
                remaining,
                bids,
                int(order.price),
                fills,
                day=day,
                timestamp=timestamp,
                product=product,
            )
            if remaining > 0 and passive_fill_mode == "trade_touch":
                _consume_passive_trade_touch(
                    remaining,
                    "SELL",
                    int(order.price),
                    prints_budget,
                    fills,
                    day=day,
                    timestamp=timestamp,
                    product=product,
                )

    return fills


def run_round1_replay(
    trader_cls,
    prices: pd.DataFrame,
    trades: pd.DataFrame,
    *,
    products: list[str] | None = None,
    passive_fill_mode: str = "trade_touch",
) -> dict[str, object]:
    products = products or list(ROUND1_PRODUCTS)
    prices = prices[prices["product"].isin(products)].copy()
    trades = trades[trades["symbol"].isin(products)].copy()

    positions = {product: 0 for product in products}
    cash = {product: 0.0 for product in products}
    last_mid = {product: 0.0 for product in products}
    fills: list[ReplayFill] = []
    equity_history: list[dict[str, float | int | str]] = []
    trader_data = ""
    trader = trader_cls()

    trades_by_timestamp = {
        key: frame.copy()
        for key, frame in trades.groupby(["day", "timestamp"], sort=True)
    }

    for (day, timestamp), snapshot in prices.groupby(["day", "timestamp"], sort=True):
        snapshot_by_product = {row.product: row for row in snapshot.itertuples(index=False)}

        order_depths = {
            product: row_to_order_depth(pd.Series(row._asdict()))
            for product, row in snapshot_by_product.items()
        }
        trades_slice = trades_by_timestamp.get((day, timestamp), pd.DataFrame(columns=trades.columns))

        state = TradingState(
            timestamp=int(timestamp),
            traderData=trader_data,
            position=positions.copy(),
            order_depths=order_depths,
            market_trades=build_market_trades(trades_slice),
            own_trades={},
            observations=Observations(),
        )

        orders_by_product, _, trader_data = trader.run(state)

        for product in products:
            row = snapshot_by_product.get(product)
            if row is not None and pd.notna(row.mid_price):
                last_mid[product] = float(row.mid_price)

            order_list = orders_by_product.get(product, [])
            if row is None or not order_list:
                continue

            row_series = pd.Series(row._asdict())
            product_trades = trades_slice[trades_slice["symbol"] == product]
            product_fills = simulate_product_orders(
                int(day),
                int(timestamp),
                product,
                order_list,
                row_series,
                product_trades,
                passive_fill_mode=passive_fill_mode,
            )

            for fill in product_fills:
                fills.append(fill)
                signed_qty = fill.quantity if fill.side == "BUY" else -fill.quantity
                positions[product] += signed_qty
                cash[product] -= fill.price * signed_qty

        for product in products:
            equity = cash[product] + positions[product] * last_mid[product]
            equity_history.append(
                {
                    "day": int(day),
                    "timestamp": int(timestamp),
                    "product": product,
                    "position": positions[product],
                    "cash": cash[product],
                    "mid_price": last_mid[product],
                    "equity": equity,
                }
            )

    fills_df = pd.DataFrame([asdict(fill) for fill in fills])
    if fills_df.empty:
        fills_df = pd.DataFrame(columns=["day", "timestamp", "product", "side", "price", "quantity", "order_price", "liquidity"])

    equity_df = pd.DataFrame(equity_history)
    summary_rows = []
    for product in products:
        product_fills = fills_df[fills_df["product"] == product]
        buys = int(product_fills.loc[product_fills["side"] == "BUY", "quantity"].sum()) if not product_fills.empty else 0
        sells = int(product_fills.loc[product_fills["side"] == "SELL", "quantity"].sum()) if not product_fills.empty else 0
        final_row = equity_df[equity_df["product"] == product].iloc[-1]
        summary_rows.append(
            {
                "product": product,
                "fills": int(len(product_fills)),
                "buy_volume": buys,
                "sell_volume": sells,
                "ending_position": int(final_row["position"]),
                "ending_cash": float(final_row["cash"]),
                "ending_equity": float(final_row["equity"]),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    return {
        "fills": fills_df,
        "equity_history": equity_df,
        "summary": summary_df,
        "assumptions": list(REPLAY_ASSUMPTIONS),
    }


def format_summary_block(summary: pd.DataFrame, warnings: list[str], passive_fill_mode: str) -> str:
    lines = [
        "Round 1 replay summary",
        f"Passive fill mode: {passive_fill_mode}",
        "Replay assumptions:",
        *[f"  - {line}" for line in REPLAY_ASSUMPTIONS],
    ]

    if warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in warnings)

    lines.append("Per-product summary:")
    for row in summary.itertuples(index=False):
        lines.append(
            "  - "
            f"{row.product}: fills={row.fills}, bought={row.buy_volume}, sold={row.sell_volume}, "
            f"ending_position={row.ending_position}, ending_cash={row.ending_cash:.2f}, ending_equity={row.ending_equity:.2f}"
        )
    return "\n".join(lines)
