import unittest

from plotly.graph_objects import Figure

from dashboard.data_loader import load_round1_bundle
from dashboard.plotting import build_market_figure, build_pnl_figure, build_position_figure
from dashboard.preprocess import build_canonical_bundle
from dashboard.replay_adapter import build_replay_tables


class PlottingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        canonical = build_canonical_bundle(load_round1_bundle())
        replay = build_replay_tables(canonical)
        cls.snapshots = canonical.snapshots
        cls.trades = canonical.trades.merge(
            canonical.snapshots[["day", "timestamp", "product", "plot_index"]],
            on=["day", "timestamp", "product"],
            how="left",
            validate="many_to_one",
        )
        cls.fills = replay.fills
        cls.equity = replay.equity

    def test_figure_builders_return_plotly_figures(self) -> None:
        product = "INTARIAN_PEPPER_ROOT"
        market = build_market_figure(self.snapshots, self.trades, self.fills, product=product, day=-2)
        position = build_position_figure(self.equity, product=product, day=-2)
        pnl = build_pnl_figure(self.equity, product=product, day=-2)

        self.assertIsInstance(market, Figure)
        self.assertIsInstance(position, Figure)
        self.assertIsInstance(pnl, Figure)
        self.assertGreater(len(market.data), 0)

    def test_empty_selection_degrades_gracefully(self) -> None:
        fig = build_market_figure(self.snapshots, self.trades, self.fills, product="MISSING", day=-2)
        self.assertIsInstance(fig, Figure)

    def test_normalization_does_not_crash_on_missing_indicator(self) -> None:
        fig = build_market_figure(
            self.snapshots,
            self.trades,
            self.fills,
            product="INTARIAN_PEPPER_ROOT",
            day=-2,
            normalization_mode="subtract",
            normalization_indicator="not_a_column",
        )
        self.assertIsInstance(fig, Figure)

    def test_trade_filters_do_not_crash(self) -> None:
        fig = build_market_figure(
            self.snapshots,
            self.trades,
            self.fills,
            product="INTARIAN_PEPPER_ROOT",
            day=-2,
            min_quantity=5,
            max_quantity=20,
            fill_side="BUY",
        )
        self.assertIsInstance(fig, Figure)

    def test_downsampling_controls_do_not_crash(self) -> None:
        fig = build_market_figure(
            self.snapshots,
            self.trades,
            self.fills,
            product="INTARIAN_PEPPER_ROOT",
            day="all",
            max_snapshots=500,
            stride=3,
        )
        self.assertIsInstance(fig, Figure)


if __name__ == "__main__":
    unittest.main()
