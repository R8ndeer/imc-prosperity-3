import unittest

from dashboard.data_loader import load_round1_bundle
from dashboard.preprocess import build_canonical_bundle
from dashboard.replay_adapter import build_replay_tables


class ReplayAdapterTest(unittest.TestCase):
    def test_replay_joins_do_not_duplicate_rows(self) -> None:
        raw = load_round1_bundle()
        canonical = build_canonical_bundle(raw)

        replay = build_replay_tables(canonical)

        self.assertEqual(len(replay.fills), len(canonical.fills))
        self.assertEqual(len(replay.equity), len(canonical.equity))
        self.assertFalse(replay.fills["plot_index"].isna().any())
        self.assertFalse(replay.equity["plot_index"].isna().any())


if __name__ == "__main__":
    unittest.main()
