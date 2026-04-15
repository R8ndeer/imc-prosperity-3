# Round 1 Microstructure Dashboard

This package is the interactive dashboard path for Round 1 research.

Module responsibilities:

- `data_loader`: raw CSV and replay-output loading.
- `preprocess`: canonical cleaned market schema and validation checks.
- `replay_adapter`: alignment of fills/equity to snapshot indices.
- `log_parser`: optional structured trader-log parsing.
- `plotting`: Plotly figure construction only.
- `layout` / `callbacks` / `app`: Dash UI wiring only.

Heavy data transformations should stay out of Dash callbacks so the dashboard
remains easy to debug and test.
