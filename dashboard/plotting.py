from __future__ import annotations

"""Plotly figure builders for microstructure dashboard panels."""

import pandas as pd
import plotly.graph_objects as go

PRICE_LEVELS = (1, 2, 3)


def empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(title=title, template="plotly_white")
    return fig


def _filter_product_day(frame: pd.DataFrame, product: str, day: int | str | None) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    out = frame[frame["product"] == product].copy()
    if day not in (None, "all"):
        out = out[out["day"] == int(day)]
    return out


def _marker_size(depth: pd.Series) -> pd.Series:
    if depth.empty:
        return depth
    clipped = depth.fillna(0).clip(lower=0)
    if clipped.max() == 0:
        return clipped + 6
    return 6 + 18 * clipped / clipped.max()


def _downsample_by_plot_index(frame: pd.DataFrame, *, stride: int = 1, max_snapshots: int | None = None) -> pd.DataFrame:
    if frame.empty or "plot_index" not in frame:
        return frame.copy()
    stride = max(int(stride or 1), 1)
    unique_count = frame["plot_index"].nunique()
    if max_snapshots and unique_count > int(max_snapshots):
        stride = max(stride, int(unique_count // int(max_snapshots)) + 1)
    return frame[frame["plot_index"] % stride == 0].copy()


def _normalized_values(values: pd.Series, base: pd.Series | None, mode: str) -> pd.Series:
    if mode == "subtract" and base is not None:
        return values - base
    return values


def _book_level_points(snapshots: pd.DataFrame, side: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    color_side = "bid" if side == "bid" else "ask"
    for level in PRICE_LEVELS:
        price_col = f"{color_side}_price_{level}"
        volume_col = f"{color_side}_volume_{level}"
        if price_col not in snapshots or volume_col not in snapshots:
            continue
        indicator_columns = [column for column in ["mid_price_clean", "wall_mid"] if column in snapshots.columns]
        level_frame = snapshots[["day", "timestamp", "product", "plot_index", price_col, volume_col, *indicator_columns]].copy()
        level_frame = level_frame.rename(columns={price_col: "price", volume_col: "depth"})
        level_frame = level_frame.dropna(subset=["price"])
        level_frame["side"] = side.upper()
        level_frame["level"] = level
        rows.extend(level_frame.to_dict("records"))
    return pd.DataFrame(rows)


def build_market_figure(
    snapshots: pd.DataFrame,
    trades: pd.DataFrame,
    fills: pd.DataFrame,
    *,
    product: str,
    day: int | str | None = "all",
    show_book: bool = True,
    show_trades: bool = True,
    show_fills: bool = True,
    indicator_overlays: list[str] | None = None,
    normalization_mode: str = "none",
    normalization_indicator: str = "wall_mid",
    min_quantity: int | float | None = None,
    max_quantity: int | float | None = None,
    fill_side: str = "all",
    max_snapshots: int | None = 4000,
    stride: int = 1,
) -> go.Figure:
    product_snapshots = _filter_product_day(snapshots, product, day)
    if product_snapshots.empty:
        return empty_figure(f"{product}: no market data")
    plot_snapshots = _downsample_by_plot_index(product_snapshots, stride=stride, max_snapshots=max_snapshots)

    indicator_overlays = indicator_overlays or []
    fig = go.Figure()

    if show_book:
        for side, color in [("bid", "#1f77b4"), ("ask", "#d62728")]:
            points = _book_level_points(plot_snapshots, side)
            if points.empty:
                continue
            base = points[normalization_indicator] if normalization_indicator in points else None
            y_values = _normalized_values(points["price"], base, normalization_mode)
            fig.add_trace(
                go.Scattergl(
                    x=points["plot_index"],
                    y=y_values,
                    mode="markers",
                    name=f"{side.upper()} levels",
                    marker={
                        "color": color,
                        "size": _marker_size(points["depth"]),
                        "opacity": 0.45,
                    },
                    customdata=points[["day", "timestamp", "product", "side", "level", "depth", "price"]],
                    hovertemplate=(
                        "day=%{customdata[0]}<br>"
                        "timestamp=%{customdata[1]}<br>"
                        "product=%{customdata[2]}<br>"
                        "side=%{customdata[3]} L%{customdata[4]}<br>"
                        "plotted price=%{y}<br>"
                        "raw price=%{customdata[6]}<br>"
                        "depth=%{customdata[5]}<extra></extra>"
                    ),
                )
            )

    for indicator in indicator_overlays:
        if indicator not in product_snapshots:
            continue
        base = plot_snapshots[normalization_indicator] if normalization_indicator in plot_snapshots else None
        y_values = _normalized_values(plot_snapshots[indicator], base, normalization_mode)
        fig.add_trace(
            go.Scatter(
                x=plot_snapshots["plot_index"],
                y=y_values,
                mode="lines",
                name=indicator,
                line={"width": 1.5},
                customdata=plot_snapshots[["day", "timestamp", "product", indicator]],
                hovertemplate=(
                    "day=%{customdata[0]}<br>"
                    "timestamp=%{customdata[1]}<br>"
                    "product=%{customdata[2]}<br>"
                    f"plotted {indicator}=%{{y}}<br>"
                    f"raw {indicator}=%{{customdata[3]}}<extra></extra>"
                ),
            )
        )

    if show_trades and not trades.empty:
        product_trades = _filter_product_day(trades, product, day)
        if min_quantity is not None:
            product_trades = product_trades[product_trades["quantity"] >= float(min_quantity)]
        if max_quantity is not None:
            product_trades = product_trades[product_trades["quantity"] <= float(max_quantity)]
        if not product_trades.empty:
            base = product_trades[normalization_indicator] if normalization_indicator in product_trades else None
            y_values = _normalized_values(product_trades["price"], base, normalization_mode)
            fig.add_trace(
                go.Scattergl(
                    x=product_trades.get("plot_index", product_trades["timestamp"]),
                    y=y_values,
                    mode="markers",
                    name="historical trades",
                    marker={"color": "#4d4d4d", "symbol": "circle", "size": _marker_size(product_trades["quantity"]), "opacity": 0.55},
                    customdata=product_trades[["day", "timestamp", "product", "quantity", "price"]],
                    hovertemplate=(
                        "day=%{customdata[0]}<br>"
                        "timestamp=%{customdata[1]}<br>"
                        "product=%{customdata[2]}<br>"
                        "plotted trade price=%{y}<br>"
                        "raw trade price=%{customdata[4]}<br>"
                        "quantity=%{customdata[3]}<extra></extra>"
                    ),
                )
            )

    if show_fills and not fills.empty:
        product_fills = _filter_product_day(fills, product, day)
        if min_quantity is not None and not product_fills.empty:
            product_fills = product_fills[product_fills["quantity"] >= float(min_quantity)]
        if max_quantity is not None and not product_fills.empty:
            product_fills = product_fills[product_fills["quantity"] <= float(max_quantity)]
        if fill_side not in (None, "all") and not product_fills.empty:
            product_fills = product_fills[product_fills["side"] == fill_side]
        for side, color, symbol in [("BUY", "#2ca02c", "triangle-up"), ("SELL", "#d62728", "triangle-down")]:
            side_fills = product_fills[product_fills["side"] == side] if not product_fills.empty else pd.DataFrame()
            if side_fills.empty:
                continue
            base = side_fills[normalization_indicator] if normalization_indicator in side_fills else None
            y_values = _normalized_values(side_fills["price"], base, normalization_mode)
            fig.add_trace(
                go.Scattergl(
                    x=side_fills.get("plot_index", side_fills["timestamp"]),
                    y=y_values,
                    mode="markers",
                    name=f"our {side.lower()} fills",
                    marker={"color": color, "symbol": symbol, "size": 11, "opacity": 0.9},
                    customdata=side_fills[["day", "timestamp", "product", "quantity", "liquidity", "price"]],
                    hovertemplate=(
                        "day=%{customdata[0]}<br>"
                        "timestamp=%{customdata[1]}<br>"
                        "product=%{customdata[2]}<br>"
                        f"side={side}<br>"
                        "plotted fill price=%{y}<br>"
                        "raw fill price=%{customdata[5]}<br>"
                        "quantity=%{customdata[3]}<br>"
                        "liquidity=%{customdata[4]}<extra></extra>"
                    ),
                )
            )

    fig.update_layout(
        title=f"{product} microstructure",
        template="plotly_white",
        xaxis_title="Snapshot index",
        yaxis_title="Price" if normalization_mode == "none" else f"Price - {normalization_indicator}",
        hovermode="closest",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        margin={"l": 60, "r": 30, "t": 80, "b": 50},
    )
    return fig


def build_position_figure(
    equity: pd.DataFrame,
    *,
    product: str,
    day: int | str | None = "all",
    max_snapshots: int | None = 4000,
    stride: int = 1,
) -> go.Figure:
    product_equity = _filter_product_day(equity, product, day)
    product_equity = _downsample_by_plot_index(product_equity, stride=stride, max_snapshots=max_snapshots)
    if product_equity.empty:
        return empty_figure(f"{product}: no position data")
    fig = go.Figure(
        go.Scatter(
            x=product_equity["plot_index"],
            y=product_equity["position"],
            mode="lines",
            name="position",
            line={"color": "#9467bd"},
        )
    )
    fig.update_layout(template="plotly_white", yaxis_title="Position", margin={"l": 60, "r": 30, "t": 20, "b": 35})
    return fig


def build_pnl_figure(
    equity: pd.DataFrame,
    *,
    product: str,
    day: int | str | None = "all",
    max_snapshots: int | None = 4000,
    stride: int = 1,
) -> go.Figure:
    product_equity = _filter_product_day(equity, product, day)
    product_equity = _downsample_by_plot_index(product_equity, stride=stride, max_snapshots=max_snapshots)
    if product_equity.empty:
        return empty_figure(f"{product}: no PnL data")
    fig = go.Figure(
        go.Scatter(
            x=product_equity["plot_index"],
            y=product_equity["equity"],
            mode="lines",
            name="equity",
            line={"color": "#2ca02c"},
        )
    )
    fig.update_layout(template="plotly_white", yaxis_title="PnL", margin={"l": 60, "r": 30, "t": 20, "b": 35})
    return fig
