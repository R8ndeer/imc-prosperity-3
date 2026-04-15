from __future__ import annotations

from dash import dcc, html


def build_layout() -> html.Div:
    """Build a placeholder layout; callbacks/data layers are added in later commits."""
    return html.Div(
        [
            html.H1("Round 1 Microstructure Dashboard"),
            html.P(
                "Dashboard package skeleton. Data loading, preprocessing, plotting, "
                "and callbacks are intentionally separated into dedicated modules."
            ),
            dcc.Graph(id="market-graph"),
        ],
        style={"fontFamily": "sans-serif", "margin": "24px"},
    )

