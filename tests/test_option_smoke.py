import unittest

from datamodel import Listing, Observation, OrderDepth, TradingState
from FrankfurtHedgehogs_polished import OPTION_SYMBOLS, OPTION_UNDERLYING_SYMBOL, OptionTrader


class OptionTraderSmokeTest(unittest.TestCase):
    def test_option_trader_runs_with_minimal_order_books(self) -> None:
        state = TradingState(
            traderData="",
            timestamp=3000,
            listings={
                symbol: Listing(symbol=symbol, product=symbol, denomination="SEASHELLS")
                for symbol in [OPTION_UNDERLYING_SYMBOL, *OPTION_SYMBOLS]
            },
            position={},
            order_depths={
                OPTION_UNDERLYING_SYMBOL: OrderDepth(
                    buy_orders={9998: 20},
                    sell_orders={10002: -20},
                ),
                "VOLCANIC_ROCK_VOUCHER_9500": OrderDepth(buy_orders={700: 10}, sell_orders={710: -10}),
                "VOLCANIC_ROCK_VOUCHER_9750": OrderDepth(buy_orders={480: 10}, sell_orders={490: -10}),
                "VOLCANIC_ROCK_VOUCHER_10000": OrderDepth(buy_orders={300: 10}, sell_orders={310: -10}),
                "VOLCANIC_ROCK_VOUCHER_10250": OrderDepth(buy_orders={180: 10}, sell_orders={190: -10}),
                "VOLCANIC_ROCK_VOUCHER_10500": OrderDepth(buy_orders={90: 10}, sell_orders={100: -10}),
            },
            observations=Observation(),
        )

        trader = OptionTrader(state, {"GENERAL": {}}, {})
        orders = trader.get_orders()

        self.assertIn(OPTION_UNDERLYING_SYMBOL, orders)
        self.assertTrue(all(symbol in orders for symbol in OPTION_SYMBOLS))


if __name__ == "__main__":
    unittest.main()
