import unittest

from datamodel import OrderDepth, TradingState
from FrankfurtHedgehogs_polished import ETF_BASKET_SYMBOLS, ETF_CONSTITUENT_SYMBOLS, EtfTrader


class EtfTraderSmokeTest(unittest.TestCase):
    def test_etf_trader_runs_without_swallowed_spread_errors(self) -> None:
        state = TradingState(
            timestamp=100,
            traderData="",
            position={},
            order_depths={
                "PICNIC_BASKET1": OrderDepth(buy_orders={1000: 10}, sell_orders={1010: -10}),
                "PICNIC_BASKET2": OrderDepth(buy_orders={700: 10}, sell_orders={710: -10}),
                "CROISSANTS": OrderDepth(buy_orders={100: 20}, sell_orders={102: -20}),
                "JAMS": OrderDepth(buy_orders={50: 20}, sell_orders={52: -20}),
                "DJEMBES": OrderDepth(buy_orders={25: 20}, sell_orders={27: -20}),
            },
        )

        trader = EtfTrader(state, {"GENERAL": {}}, {})
        orders = trader.get_orders()

        self.assertEqual(len(trader.spreads), 2)
        self.assertTrue(all(spread is not None for spread in trader.spreads))
        self.assertTrue(all(symbol in orders for symbol in ETF_BASKET_SYMBOLS))
        self.assertTrue(all(symbol in orders for symbol in ETF_CONSTITUENT_SYMBOLS))


if __name__ == "__main__":
    unittest.main()
