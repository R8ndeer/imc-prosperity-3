from __future__ import annotations

from dash import Dash

from dashboard.callbacks import register_callbacks
from dashboard.layout import build_layout


def create_app() -> Dash:
    """Create the Dash app without doing heavy data work at import time."""
    app = Dash(__name__, suppress_callback_exceptions=True)
    app.title = "Round 1 Microstructure Dashboard"
    app.layout = build_layout()
    register_callbacks(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)

