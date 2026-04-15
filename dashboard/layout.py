from __future__ import annotations

from dash import dcc, html

from dashboard.state import day_options, load_dashboard_data, product_options


def build_layout() -> html.Div:
    data = load_dashboard_data()
    products = product_options(data)
    days = day_options(data)
    default_product = products[0]["value"] if products else None

    return html.Div(
        [
            html.H1("Round 1 Microstructure Dashboard"),
            html.Div(
                [
                    html.Label("Product"),
                    dcc.Dropdown(id="product-dropdown", options=products, value=default_product, clearable=False),
                    html.Label("Day"),
                    dcc.Dropdown(id="day-dropdown", options=days, value="all", clearable=False),
                    html.Label("Indicator Overlays"),
                    dcc.Checklist(
                        id="indicator-checklist",
                        options=[
                            {"label": "Mid Price", "value": "mid_price_clean"},
                            {"label": "Wall Mid", "value": "wall_mid"},
                        ],
                        value=["wall_mid"],
                        inline=True,
                    ),
                    html.Label("Normalization"),
                    dcc.Dropdown(
                        id="normalization-dropdown",
                        options=[
                            {"label": "None", "value": "none"},
                            {"label": "Subtract selected indicator", "value": "subtract"},
                        ],
                        value="none",
                        clearable=False,
                    ),
                    html.Label("Normalize By"),
                    dcc.Dropdown(
                        id="normalization-indicator-dropdown",
                        options=[
                            {"label": "Wall Mid", "value": "wall_mid"},
                            {"label": "Mid Price", "value": "mid_price_clean"},
                        ],
                        value="wall_mid",
                        clearable=False,
                    ),
                    dcc.Checklist(
                        id="visibility-checklist",
                        options=[
                            {"label": "Book levels", "value": "book"},
                            {"label": "Historical trades", "value": "trades"},
                            {"label": "Own fills", "value": "fills"},
                        ],
                        value=["book", "trades", "fills"],
                        inline=True,
                    ),
                    html.Label("Min Qty"),
                    dcc.Input(id="min-quantity-input", type="number", min=0, step=1, value=0),
                    html.Label("Max Qty"),
                    dcc.Input(id="max-quantity-input", type="number", min=0, step=1, value=None),
                    html.Label("Fill Side"),
                    dcc.Dropdown(
                        id="fill-side-dropdown",
                        options=[
                            {"label": "All", "value": "all"},
                            {"label": "Buys", "value": "BUY"},
                            {"label": "Sells", "value": "SELL"},
                        ],
                        value="all",
                        clearable=False,
                    ),
                    html.Label("Max Snapshots"),
                    dcc.Input(id="max-snapshots-input", type="number", min=100, step=100, value=4000),
                    html.Label("Stride"),
                    dcc.Input(id="stride-input", type="number", min=1, step=1, value=1),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr 2fr 1fr 1fr 1fr 1fr 1fr 1fr",
                    "gap": "12px",
                    "alignItems": "end",
                    "marginBottom": "16px",
                },
            ),
            dcc.Graph(id="market-graph", style={"height": "620px"}),
            html.Div(
                [
                    dcc.Graph(id="position-graph", style={"height": "230px"}),
                    dcc.Graph(id="pnl-graph", style={"height": "230px"}),
                ],
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"},
            ),
            html.Div(id="details-panel", style={"marginTop": "16px", "padding": "12px", "border": "1px solid #ddd"}),
        ],
        style={"fontFamily": "sans-serif", "margin": "20px"},
    )
