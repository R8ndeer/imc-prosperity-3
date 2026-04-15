import unittest

import pandas as pd

from dashboard.data_loader import load_round1_bundle
from dashboard.preprocess import clean_snapshots, validate_snapshots


class DashboardPreprocessTest(unittest.TestCase):
    def test_clean_snapshots_do_not_introduce_zero_prices(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "day": 0,
                    "timestamp": 0,
                    "product": "TEST",
                    "bid_price_1": pd.NA,
                    "bid_volume_1": pd.NA,
                    "bid_price_2": pd.NA,
                    "bid_volume_2": pd.NA,
                    "bid_price_3": pd.NA,
                    "bid_volume_3": pd.NA,
                    "ask_price_1": 0,
                    "ask_volume_1": 5,
                    "ask_price_2": pd.NA,
                    "ask_volume_2": pd.NA,
                    "ask_price_3": pd.NA,
                    "ask_volume_3": pd.NA,
                    "mid_price": 0,
                    "profit_and_loss": 0,
                }
            ]
        )

        snapshots = clean_snapshots(raw)

        self.assertTrue(pd.isna(snapshots.loc[0, "best_bid"]))
        self.assertTrue(pd.isna(snapshots.loc[0, "best_ask"]))
        self.assertTrue(pd.isna(snapshots.loc[0, "mid_price_clean"]))
        self.assertTrue(bool(snapshots.loc[0, "book_missing"]))

    def test_real_round1_snapshot_validation_passes(self) -> None:
        raw_bundle = load_round1_bundle()
        snapshots = clean_snapshots(raw_bundle.prices)

        errors = validate_snapshots(snapshots)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
