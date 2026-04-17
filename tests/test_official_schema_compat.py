import unittest

import FrankfurtHedgehogs_polished as prosperity3_trader
from datamodel import (
    Listing,
    Observation,
    Observations,
    OrderDepth,
    TradingState,
)


class OfficialSchemaCompatibilityTest(unittest.TestCase):
    def test_official_style_trading_state_instantiates(self) -> None:
        state = TradingState(
            traderData="persisted-state",
            timestamp=0,
            listings={
                "RAINFOREST_RESIN": Listing(
                    symbol="RAINFOREST_RESIN",
                    product="RAINFOREST_RESIN",
                    denomination="SEASHELLS",
                )
            },
            order_depths={
                "RAINFOREST_RESIN": OrderDepth(
                    buy_orders={9998: 5},
                    sell_orders={10002: -7},
                )
            },
            own_trades={},
            market_trades={},
            position={},
            observations=Observation(),
        )

        self.assertEqual(state.listings["RAINFOREST_RESIN"].product, "RAINFOREST_RESIN")
        self.assertEqual(state.order_depths["RAINFOREST_RESIN"].sell_orders[10002], -7)

    def test_legacy_trader_runs_against_official_style_state(self) -> None:
        state = TradingState(
            traderData="",
            timestamp=0,
            listings={
                "RAINFOREST_RESIN": Listing(
                    symbol="RAINFOREST_RESIN",
                    product="RAINFOREST_RESIN",
                    denomination="SEASHELLS",
                )
            },
            order_depths={
                "RAINFOREST_RESIN": OrderDepth(
                    buy_orders={9998: 5},
                    sell_orders={10002: -5},
                )
            },
            own_trades={},
            market_trades={},
            position={},
            observations=Observation(),
        )

        result = prosperity3_trader.Trader().run(state)

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], dict)
        self.assertIsInstance(result[1], int)
        self.assertIsInstance(result[2], str)

    def test_observation_alias_remains_compatible(self) -> None:
        canonical = Observation()
        alias = Observations()

        self.assertIsInstance(canonical, Observation)
        self.assertIsInstance(alias, Observation)
        self.assertEqual(canonical.plainValueObservations, {})
        self.assertEqual(alias.conversionObservations, {})

    def test_order_depth_sell_orders_accept_negative_quantities(self) -> None:
        depth = OrderDepth(sell_orders={101: -3, 102: -8})

        self.assertEqual(depth.sell_orders[101], -3)
        self.assertTrue(all(quantity < 0 for quantity in depth.sell_orders.values()))


if __name__ == "__main__":
    unittest.main()
