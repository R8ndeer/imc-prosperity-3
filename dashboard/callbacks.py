from __future__ import annotations

import pandas as pd
from dash import Dash, Input, Output, html

from dashboard.plotting import build_market_figure, build_pnl_figure, build_position_figure
from dashboard.replay_adapter import details_for_timestamp
from dashboard.state import load_dashboard_data


def _extract_hover_key(hover_data, fallback_product):
    if not hover_data:
        return None
    point = hover_data.get("points", [{}])[0]
    custom = point.get("customdata") or []
    if len(custom) < 3:
        return None
    try:
        return int(custom[0]), int(custom[1]), str(custom[2])
    except Exception:
        return None


def _format_value(value) -> str:
    if pd.isna(value):
        return "missing"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _ladder_rows(snapshot: dict[str, object]) -> list[html.Tr]:
    rows = []
    for level in (1, 2, 3):
        rows.append(
            html.Tr(
                [
                    html.Td(f"L{level}"),
                    html.Td(_format_value(snapshot.get(f"bid_price_{level}"))),
                    html.Td(_format_value(snapshot.get(f"bid_volume_{level}"))),
                    html.Td(_format_value(snapshot.get(f"ask_price_{level}"))),
                    html.Td(_format_value(snapshot.get(f"ask_volume_{level}"))),
                ]
            )
        )
    return rows


def _small_table(records: list[dict[str, object]], columns: list[str], empty_label: str):
    if not records:
        return html.Div(empty_label, style={"color": "#777"})
    return html.Table(
        [
            html.Thead(html.Tr([html.Th(column) for column in columns])),
            html.Tbody(
                [
                    html.Tr([html.Td(_format_value(record.get(column))) for column in columns])
                    for record in records[:12]
                ]
            ),
        ],
        style={"fontSize": "12px", "borderCollapse": "collapse"},
    )


def _render_details(details: dict[str, object], *, day: int, timestamp: int, product: str):
    snapshot = details.get("snapshot", {})
    equity = details.get("equity", {})
    return html.Div(
        [
            html.H3(f"{product} | day {day} | timestamp {timestamp}"),
            html.Div(
                [
                    html.Div(
                        [
                            html.H4("Snapshot"),
                            html.Div(f"best bid: {_format_value(snapshot.get('best_bid'))}"),
                            html.Div(f"best ask: {_format_value(snapshot.get('best_ask'))}"),
                            html.Div(f"wall mid: {_format_value(snapshot.get('wall_mid'))}"),
                            html.Div(f"spread: {_format_value(snapshot.get('spread'))}"),
                            html.Div(f"book missing: {_format_value(snapshot.get('book_missing'))}"),
                        ]
                    ),
                    html.Div(
                        [
                            html.H4("Visible Ladder"),
                            html.Table(
                                [
                                    html.Thead(
                                        html.Tr([html.Th("Level"), html.Th("Bid"), html.Th("Bid Qty"), html.Th("Ask"), html.Th("Ask Qty")])
                                    ),
                                    html.Tbody(_ladder_rows(snapshot)),
                                ],
                                style={"fontSize": "12px", "borderCollapse": "collapse"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.H4("Replay State"),
                            html.Div(f"position: {_format_value(equity.get('position'))}"),
                            html.Div(f"cash: {_format_value(equity.get('cash'))}"),
                            html.Div(f"equity / pnl: {_format_value(equity.get('equity'))}"),
                        ]
                    ),
                ],
                style={"display": "grid", "gridTemplateColumns": "1fr 1.4fr 1fr", "gap": "16px"},
            ),
            html.Div(
                [
                    html.Div([html.H4("Historical Trades"), _small_table(details.get("trades", []), ["price", "quantity", "buyer", "seller"], "No trades")]),
                    html.Div([html.H4("Our Fills"), _small_table(details.get("fills", []), ["side", "price", "quantity", "liquidity"], "No fills")]),
                ],
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginTop": "12px"},
            ),
            html.Div(
                [
                    html.H4("Logs"),
                    _small_table(details.get("logs", []), ["group", "key", "value"], "No parsed logs for this timestamp"),
                ],
                style={"marginTop": "12px"},
            ),
        ]
    )


def register_callbacks(app: Dash) -> None:
    @app.callback(
        Output("market-graph", "figure"),
        Output("position-graph", "figure"),
        Output("pnl-graph", "figure"),
        Input("product-dropdown", "value"),
        Input("day-dropdown", "value"),
        Input("indicator-checklist", "value"),
        Input("visibility-checklist", "value"),
        Input("normalization-dropdown", "value"),
        Input("normalization-indicator-dropdown", "value"),
        Input("min-quantity-input", "value"),
        Input("max-quantity-input", "value"),
        Input("fill-side-dropdown", "value"),
        Input("max-snapshots-input", "value"),
        Input("stride-input", "value"),
    )
    def update_figures(
        product,
        day,
        indicators,
        visibility,
        normalization,
        normalization_indicator,
        min_quantity,
        max_quantity,
        fill_side,
        max_snapshots,
        stride,
    ):
        data = load_dashboard_data()
        visibility = visibility or []
        indicators = indicators or []

        market = build_market_figure(
            data.snapshots,
            data.trades,
            data.fills,
            product=product,
            day=day,
            show_book="book" in visibility,
            show_trades="trades" in visibility,
            show_fills="fills" in visibility,
            indicator_overlays=indicators,
            normalization_mode=normalization or "none",
            normalization_indicator=normalization_indicator or "wall_mid",
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            fill_side=fill_side or "all",
            max_snapshots=max_snapshots or 4000,
            stride=stride or 1,
        )
        position = build_position_figure(data.equity, product=product, day=day, max_snapshots=max_snapshots or 4000, stride=stride or 1)
        pnl = build_pnl_figure(data.equity, product=product, day=day, max_snapshots=max_snapshots or 4000, stride=stride or 1)
        return market, position, pnl

    @app.callback(
        Output("details-panel", "children"),
        Input("market-graph", "hoverData"),
        Input("product-dropdown", "value"),
    )
    def update_details(hover_data, product):
        key = _extract_hover_key(hover_data, product)
        if key is None:
            return html.Div(f"Hover over {product} market points to inspect timestamp details.")

        day, timestamp, hovered_product = key
        data = load_dashboard_data()
        details = details_for_timestamp(
            data.snapshots,
            data.trades,
            data.fills,
            data.equity,
            data.logs,
            day=day,
            timestamp=timestamp,
            product=hovered_product,
        )
        return _render_details(details, day=day, timestamp=timestamp, product=hovered_product)
