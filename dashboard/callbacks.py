from __future__ import annotations

from dash import Dash, Input, Output, html

from dashboard.plotting import build_market_figure, build_pnl_figure, build_position_figure
from dashboard.state import load_dashboard_data


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
    )
    def update_figures(product, day, indicators, visibility, normalization):
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
        )
        position = build_position_figure(data.equity, product=product, day=day)
        pnl = build_pnl_figure(data.equity, product=product, day=day)
        return market, position, pnl

    @app.callback(
        Output("details-panel", "children"),
        Input("market-graph", "hoverData"),
        Input("product-dropdown", "value"),
    )
    def placeholder_details(hover_data, product):
        if not hover_data:
            return html.Div(f"Hover over {product} market points to inspect timestamp details.")
        point = hover_data.get("points", [{}])[0]
        custom = point.get("customdata", [])
        return html.Pre(f"Hovered point custom data: {custom}")
