# Project Context

## Environment

- Conda env: `miracledog`
- Repo root: `/Users/liboting/imc-prosperity-3`

## Main Tracks

### 1. Legacy Prosperity 3 Reference

- `FrankfurtHedgehogs_polished.py`
- `README.md`
- Use as reference only for old strategy ideas and structure.

### 2. New Round 1 Local Baseline / Replay

- `round1_baseline_trader.py`
- `scripts/backtest_round1.py`
- `scripts/round1_data_utils.py`
- `scripts/visualize_round1.py`
- Historical data lives in `ROUND1/`

Current replay outputs are expected in:

- `output/round1/round1_fills.csv`
- `output/round1/round1_equity_history.csv`
- `output/round1/round1_summary.csv`
- `output/round1/round1_assumptions.json`

### 3. Interactive Dashboard

- Package: `dashboard/`
- Entry point: `python -m dashboard.app`
- Cache builder: `python -m dashboard.build_cache --cache-dir output/dashboard_cache`
- Debug exporter: `python scripts/visualize_round1.py --output-dir output/round1_debug_figures`

Default dashboard paths:

- raw data: `ROUND1/`
- replay outputs: `output/round1/`
- dashboard cache: `output/dashboard_cache/`
- logs: `output/round1/logs/`

## Important Datamodel State

- `datamodel.py` is aligned to the official Prosperity-style schema
- Canonical names:
  - `Observation`
  - `TradingState.listings`
  - `TradingState.observations`
  - `OrderDepth.sell_orders` keeps raw negative quantities
- Compatibility alias exists:
  - `Observations = Observation`

### Official Wiki Mismatch

`ConversionObservation` in the official wiki is inconsistent.

Current local handling:

- constructor supports `sunlight` / `humidity`
- compatibility fields also exposed:
  - `sunlightIndex`
  - `sugarPrice`

## Recent Important Commits

- `b3b6956` align datamodel with official prosperity schema
- `026ffa6` add defensive ConversionObservation compatibility for wiki mismatch
- `aaf4abe` use official-style datamodel objects in local replay scaffolding
- `2af97a8` add smoke tests for official-schema datamodel compatibility
- `5470f98` add optional bid method compatibility shim
- `281ac87` convert static replay plotter into secondary debug utility
- `ae9f8b0` add processed dashboard cache support

## Useful Commands

Run Round 1 replay:

```bash
conda activate miracledog
cd /Users/liboting/imc-prosperity-3
python scripts/backtest_round1.py --data-dir ROUND1 --output-dir output/round1
```

Rebuild dashboard cache:

```bash
python -m dashboard.build_cache --cache-dir output/dashboard_cache
```

Run dashboard:

```bash
python -m dashboard.app
```

Run key schema/replay tests:

```bash
python -m unittest tests.test_smoke tests.test_product_smoke tests.test_option_smoke tests.test_etf_smoke tests.test_official_schema_compat
python -m unittest tests.dashboard.test_preprocess tests.dashboard.test_replay_adapter tests.dashboard.test_plotting tests.dashboard.test_log_parser
```

## Current Important Limitations

- Dashboard prefers cached processed data if cache exists.
- If replay outputs change, rebuild cache or the dashboard may show stale data.
- `pyarrow` is not installed, so dashboard cache currently uses CSV, not parquet.
- Replay engine is a research replay, not an exact official simulator.
- Legacy Prosperity 3 strategy code still has product-specific assumptions.

## Things To Remember Next

- If switching to a new replay result set, easiest current path is rebuilding `output/dashboard_cache` from that result set.
- Keep new work modular; do not refactor legacy strategy files unless explicitly needed.
- If more official wiki/docs arrive, compare them against `datamodel.py` first before changing replay/dashboard layers.
