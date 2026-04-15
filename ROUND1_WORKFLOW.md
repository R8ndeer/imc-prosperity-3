# Round 1 Simulation And Dashboard Workflow

This guide explains how to run the current local Round 1 replay simulation and how to use the interactive microstructure dashboard.

The current workflow is a research setup, not an exact clone of the official simulator. Its job is to help us inspect the new Round 1 products, compare baseline behavior, and debug fills, inventory, and PnL.

## Quick Start

Use the `miracledog` conda environment:

```bash
conda activate miracledog
```

From the repo root:

```bash
cd /Users/liboting/imc-prosperity-3
```

Run the Round 1 replay:

```bash
python scripts/backtest_round1.py --data-dir ROUND1 --output-dir output/round1
```

Build or refresh dashboard cache:

```bash
python -m dashboard.build_cache --cache-dir output/dashboard_cache
```

Launch the dashboard:

```bash
python -m dashboard.app
```

Then open the local URL printed by Dash, usually:

```text
http://127.0.0.1:8050
```

## 1. Running The Trading Simulation

The current Round 1 strategy is in:

```text
round1_baseline_trader.py
```

It is intentionally separate from the old Prosperity 3 source files. It contains only this year’s Round 1 products:

- `INTARIAN_PEPPER_ROOT`
- `ASH_COATED_OSMIUM`

The replay script is:

```text
scripts/backtest_round1.py
```

It reads historical CSVs from:

```text
ROUND1/
```

Expected input files:

```text
prices_round_1_day_-2.csv
prices_round_1_day_-1.csv
prices_round_1_day_0.csv
trades_round_1_day_-2.csv
trades_round_1_day_-1.csv
trades_round_1_day_0.csv
```

### Basic Command

```bash
python scripts/backtest_round1.py --data-dir ROUND1 --output-dir output/round1
```

This writes:

```text
output/round1/round1_fills.csv
output/round1/round1_equity_history.csv
output/round1/round1_summary.csv
output/round1/round1_assumptions.json
```

### Passive Fill Modes

The backtester supports two passive fill modes:

```bash
python scripts/backtest_round1.py --passive-fill-mode trade_touch
```

`trade_touch` is the default. It fills passive orders only when historical market trades touch our order price, capped by the historical traded quantity at that timestamp.

```bash
python scripts/backtest_round1.py --passive-fill-mode none
```

`none` disables passive fills. This is useful for a conservative sanity check because it shows only fills that cross visible book depth.

### What The Replay Assumes

The replay is timestamp-by-timestamp:

- the strategy sees the visible order book snapshot at each timestamp
- aggressive buys fill against visible ask depth level by level
- aggressive sells fill against visible bid depth level by level
- passive fills are heuristic, not official simulator behavior
- historical market trades are diagnostics unless used by the chosen passive-fill heuristic
- PnL is marked to the snapshot `mid_price`

Important: this replay is for research. Do not treat the resulting PnL as official competition PnL.

### When To Rerun The Replay

Rerun `scripts/backtest_round1.py` when:

- you change `round1_baseline_trader.py`
- you change replay assumptions in `scripts/round1_data_utils.py`
- you add new historical data
- you want to compare `trade_touch` versus `none`

After rerunning replay, rebuild dashboard cache:

```bash
python -m dashboard.build_cache --cache-dir output/dashboard_cache
```

## 2. What The Dashboard Does

The dashboard is the main research interface for inspecting market microstructure. It is inspired by the dashboard philosophy in the old README: focus on order-book structure, trades, fills, position, PnL, and timestamp-synced details.

The dashboard code lives in:

```text
dashboard/
```

Important modules:

- `dashboard/data_loader.py`: loads raw Round 1 CSVs and replay outputs
- `dashboard/preprocess.py`: builds cleaned canonical market tables
- `dashboard/replay_adapter.py`: aligns fills and equity to market snapshots
- `dashboard/plotting.py`: builds Plotly figures
- `dashboard/layout.py`: defines Dash UI layout
- `dashboard/callbacks.py`: wires UI controls to figures and details
- `dashboard/log_parser.py`: parses structured logs if available
- `dashboard/build_cache.py`: builds processed cache files

The current dashboard is purpose-built for Round 1. It is not a generic trading dashboard.

## Dashboard Controls

### Product Dropdown

Use this to choose one product at a time:

- `INTARIAN_PEPPER_ROOT`
- `ASH_COATED_OSMIUM`

Use it when comparing whether the old stable-product baseline behaves better on Pepper Root than Osmium.

### Day Selector

Options:

- `All days`
- `Day -2`
- `Day -1`
- `Day 0`

Use single-day views when:

- the all-day chart is too dense
- you want to inspect one day’s market regime
- you are debugging a specific fill or position swing

Use all days when:

- you want a quick overview
- you are looking for repeated behavior across days

### Indicator Overlays

Current overlays include:

- `Mid Price`
- `Wall Mid`

`Wall Mid` is the old Prosperity-style fair-value proxy: it uses visible bid/ask book walls rather than just top-of-book.

Use overlays to answer:

- are our quotes centered around the intended fair value?
- does the product behave like a stable market-making product?
- are fills happening far from fair value or near it?

### Normalization

Normalization lets you transform the plotted y-axis by subtracting an indicator.

Current modes:

- `None`
- `Subtract selected indicator`

Current normalization indicators:

- `Wall Mid`
- `Mid Price`

Example: choose `Subtract selected indicator` and `Wall Mid`.

This changes the market plot from raw prices to:

```text
price - wall_mid
```

Use normalization when:

- raw prices drift and hide microstructure patterns
- you want to see whether bid/ask levels are symmetric around fair value
- you want to compare trade/fill edge relative to wall mid

Important: hover/details still preserve raw values, so normalized charts remain debuggable.

### Visibility Toggles

Controls:

- `Book levels`
- `Historical trades`
- `Own fills`

Use `Book levels` to inspect visible liquidity.

Use `Historical trades` to see where market activity occurred in the historical simulation.

Use `Own fills` to see where our replay assumptions say the baseline traded.

Useful debugging patterns:

- turn off trades to inspect only the book and our fills
- turn off fills to understand the raw market first
- turn off book levels if trades/fills are visually crowded

### Quantity Filters

Controls:

- `Min Qty`
- `Max Qty`

These filter historical trades and own fills by quantity.

Use them when:

- small prints clutter the chart
- you want to identify larger market activity
- you want to inspect whether our larger fills happen at poor prices

### Fill Side Filter

Options:

- `All`
- `Buys`
- `Sells`

Use this to isolate our replay buys or sells.

This is especially useful for checking inventory behavior:

- if PnL drops after buy fills, were buys happening too high?
- if PnL drops after sell fills, were sells happening too low?
- did the strategy get stuck long or short?

### Max Snapshots

This controls dashboard responsiveness by limiting how many book snapshots are plotted.

Default:

```text
4000
```

Use lower values if:

- the dashboard feels slow
- you are viewing all days
- you only need a broad overview

Use higher values if:

- you are focused on one day
- you need detailed timestamp-level inspection

### Stride

Stride plots every Nth snapshot.

Examples:

```text
1 = plot every snapshot
5 = plot every 5th snapshot
10 = plot every 10th snapshot
```

Use stride when:

- the order-book scatter is too dense
- browser rendering is slow
- you want a quick overview before zooming in

Fills are not aggressively downsampled by default, because they are usually much more important for debugging.

### Logs Selector

The dashboard has log parsing plumbing, but current replay outputs may not include structured log files.

If logs are available later, the details panel can show timestamp-synced log values.

Until then, the panel will show:

```text
No parsed logs for this timestamp
```

## Dashboard Panels

### Main Market Panel

This is the most important panel.

It shows:

- bid order-book levels as blue scatter points
- ask order-book levels as red scatter points
- marker size based on visible depth
- historical trades as grey markers
- our simulated buys as green upward triangles
- our simulated sells as red downward triangles
- optional fair-value overlays as lines

Why scatter instead of lines?

The order book is sparse and level-based. Continuous lines can imply fake price paths. Scatter points better represent visible microstructure.

Use the main panel to answer:

- where was liquidity sitting?
- did the book have missing sides?
- did trades happen inside, at, or outside the visible spread?
- did our fills happen at sensible prices?
- does the product look stable, drifting, or jumpy?

### Position Panel

Shows replay inventory over time.

Use it to answer:

- did the strategy stay within position limits?
- did it get stuck long or short?
- did it unwind inventory after taking risk?
- did position swings match visible market conditions?

Position is often more informative than PnL early in strategy debugging.

### PnL Panel

Shows replay equity / marked PnL over time.

Use it to answer:

- where did the baseline make or lose money?
- are losses tied to inventory buildup?
- are PnL jumps tied to replay fill assumptions?
- does `trade_touch` produce suspiciously optimistic fills?

Remember: replay PnL is approximate, not official simulator PnL.

### Timestamp Details Panel

Hover over the main market plot to update the details panel.

It shows:

- day
- timestamp
- product
- visible bid/ask ladder
- best bid
- best ask
- wall mid
- spread
- whether the book is missing
- historical trades at that timestamp
- our fills at that timestamp
- replay position, cash, and PnL
- parsed logs if available

Use it when a point on the chart looks suspicious:

- a strange fill
- a large trade
- a missing book snapshot
- a sudden PnL jump
- a position reversal

This panel is meant to replace guessing from hover text alone.

## Missing Book Handling

Some snapshots have missing visible bid or ask levels.

The preprocessing layer treats missing levels as missing values, not zero prices.

This matters because plotting missing prices as `0` creates fake vertical crashes in the chart.

If a book side is missing:

- the line/scatter value is absent
- details panel marks `book_missing`
- indicators depending on both sides may be missing

This is expected and safer than inventing data.

## Typical Research Workflow

### First Pass: Broad Overview

1. Run replay:

```bash
python scripts/backtest_round1.py --data-dir ROUND1 --output-dir output/round1
```

2. Build cache:

```bash
python -m dashboard.build_cache --cache-dir output/dashboard_cache
```

3. Launch dashboard:

```bash
python -m dashboard.app
```

4. Select `All days`.
5. Keep `Wall Mid` overlay on.
6. Keep `Book levels`, `Historical trades`, and `Own fills` enabled.
7. Use `Max Snapshots` or `Stride` if the chart feels crowded.

Goal: understand each product’s overall structure.

### Inspect Pepper Root Baseline

1. Product: `INTARIAN_PEPPER_ROOT`
2. Normalization: `Subtract selected indicator`
3. Normalize By: `Wall Mid`
4. Overlay: `Wall Mid`
5. Look for fills above/below normalized fair value.

Questions:

- does the stable-product baseline quote symmetrically?
- does it mostly buy below wall mid and sell above wall mid?
- does inventory mean-revert or drift?

### Inspect Osmium Baseline

1. Product: `ASH_COATED_OSMIUM`
2. Start with raw prices.
3. Then normalize by wall mid.
4. Compare historical trades and our fills.

Questions:

- does Osmium look stable enough for symmetric market making?
- are there jumps or missing-book periods?
- does our baseline get adversely positioned?

### Compare Replay Assumptions

Run once with passive fills:

```bash
python scripts/backtest_round1.py --passive-fill-mode trade_touch
python -m dashboard.build_cache --cache-dir output/dashboard_cache
```

Then run conservative mode:

```bash
python scripts/backtest_round1.py --passive-fill-mode none
python -m dashboard.build_cache --cache-dir output/dashboard_cache
```

Compare fills and PnL.

If `trade_touch` looks much better than `none`, inspect whether the passive fill heuristic is too optimistic.

## Debug HTML Export

The old static PNG plotter has been replaced by a secondary debug exporter:

```bash
python scripts/visualize_round1.py --output-dir output/round1_debug_figures
```

This writes standalone Plotly HTML files for quick inspection or sharing.

Use this when:

- you do not need the full Dash app
- you want an offline artifact
- you want a quick sanity check of the dashboard plotting stack

The interactive dashboard is still the primary path.

## Running Tests

Dashboard-focused tests:

```bash
python -m unittest \
  tests.dashboard.test_preprocess \
  tests.dashboard.test_replay_adapter \
  tests.dashboard.test_plotting \
  tests.dashboard.test_log_parser
```

These check:

- no fake zero price placeholders in cleaned market data
- stable plot indices
- replay joins do not duplicate rows
- figure builders return Plotly figures
- normalization and filters do not crash
- log parser handles simple structured logs

## Current Limitations

- The local replay is approximate.
- Passive fills are heuristic.
- Historical trades do not prove our passive orders would have filled.
- Trade maker/taker classification is not inferred yet.
- Informed-trader classification is not implemented.
- Logs are supported, but current replay outputs may not contain structured logs.
- Dashboard cache uses CSV unless `pyarrow` is installed.

## When To Use Which Tool

Use `scripts/backtest_round1.py` when:

- you changed strategy logic
- you changed replay assumptions
- you need fresh fills, position, and PnL

Use `dashboard.build_cache` when:

- replay outputs changed
- raw CSVs changed
- dashboard data feels stale

Use `dashboard.app` when:

- you want interactive market inspection
- you want hover-synced details
- you want normalization, filters, and downsampling

Use `scripts/visualize_round1.py` when:

- you want standalone HTML debug figures
- you do not need interactivity beyond Plotly’s built-in zoom/hover

