import unittest

from datamodel import OrderDepth, TradingState
from FrankfurtHedgehogs_polished import Trader


class TraderSmokeTest(unittest.TestCase):
    def test_trader_runs_on_minimal_static_product(self) -> None:
        state = TradingState(
            timestamp=0,
            traderData="",
            position={},
            order_depths={
                "RAINFOREST_RESIN": OrderDepth(
                    buy_orders={9998: 5, 9997: 5},
                    sell_orders={10002: -5, 10003: -5},
                )
            },
        )

        result = Trader().run(state)

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

        orders, conversions, trader_data = result
        self.assertIsInstance(orders, dict)
        self.assertIsInstance(conversions, int)
        self.assertIsInstance(trader_data, str)


if __name__ == "__main__":
    unittest.main()
