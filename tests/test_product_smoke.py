import unittest

from datamodel import ConversionObservation, Listing, Observation, Observations, OrderDepth, TradingState
from FrankfurtHedgehogs_polished import (
    COMMODITY_SYMBOL,
    DYNAMIC_SYMBOL,
    ETF_BASKET_SYMBOLS,
    ETF_CONSTITUENT_SYMBOLS,
    OPTION_SYMBOLS,
    OPTION_UNDERLYING_SYMBOL,
    CommodityTrader,
    DynamicTrader,
    EtfTrader,
    OptionTrader,
    STATIC_SYMBOL,
    StaticTrader,
)


def make_state(
    *,
    timestamp: int = 100,
    order_depths: dict[str, OrderDepth] | None = None,
    observations: Observation | None = None,
) -> TradingState:
    products = set((order_depths or {}).keys())
    return TradingState(
        traderData="",
        timestamp=timestamp,
        listings={product: Listing(symbol=product, product=product, denomination="XIRECS") for product in products},
        position={},
        order_depths=order_depths or {},
        market_trades={},
        own_trades={},
        observations=observations or Observation(),
    )


class ProductSmokeTest(unittest.TestCase):
    def test_static_trader_runs(self) -> None:
        state = make_state(
            order_depths={
                STATIC_SYMBOL: OrderDepth(
                    buy_orders={9998: 5, 9997: 5},
                    sell_orders={10002: -5, 10003: -5},
                )
            }
        )

        orders = StaticTrader(state, {"GENERAL": {}}, {}).get_orders()

        self.assertIn(STATIC_SYMBOL, orders)
        self.assertIsInstance(orders[STATIC_SYMBOL], list)

    def test_dynamic_trader_runs(self) -> None:
        state = make_state(
            order_depths={
                DYNAMIC_SYMBOL: OrderDepth(
                    buy_orders={9999: 8, 9998: 8},
                    sell_orders={10001: -8, 10002: -8},
                )
            }
        )

        orders = DynamicTrader(state, {"GENERAL": {}}, {}).get_orders()

        self.assertIn(DYNAMIC_SYMBOL, orders)
        self.assertIsInstance(orders[DYNAMIC_SYMBOL], list)

    def test_etf_trader_runs(self) -> None:
        state = make_state(
            order_depths={
                "PICNIC_BASKET1": OrderDepth(buy_orders={1000: 10}, sell_orders={1010: -10}),
                "PICNIC_BASKET2": OrderDepth(buy_orders={700: 10}, sell_orders={710: -10}),
                "CROISSANTS": OrderDepth(buy_orders={100: 20}, sell_orders={102: -20}),
                "JAMS": OrderDepth(buy_orders={50: 20}, sell_orders={52: -20}),
                "DJEMBES": OrderDepth(buy_orders={25: 20}, sell_orders={27: -20}),
            }
        )

        orders = EtfTrader(state, {"GENERAL": {}}, {}).get_orders()

        self.assertTrue(all(symbol in orders for symbol in ETF_BASKET_SYMBOLS))
        self.assertTrue(all(symbol in orders for symbol in ETF_CONSTITUENT_SYMBOLS))

    def test_option_trader_runs(self) -> None:
        state = make_state(
            timestamp=3000,
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
        )

        orders = OptionTrader(state, {"GENERAL": {}}, {}).get_orders()

        self.assertIn(OPTION_UNDERLYING_SYMBOL, orders)
        self.assertTrue(all(symbol in orders for symbol in OPTION_SYMBOLS))

    def test_conversion_trader_runs(self) -> None:
        state = make_state(
            order_depths={
                COMMODITY_SYMBOL: OrderDepth(
                    buy_orders={105: 6, 104: 6},
                    sell_orders={109: -6, 110: -6},
                )
            },
            observations=Observations(
                conversionObservations={
                    COMMODITY_SYMBOL: ConversionObservation(
                        bidPrice=108,
                        askPrice=103,
                        transportFees=1,
                        exportTariff=1,
                        importTariff=1,
                        sunlightIndex=50,
                        sugarPrice=75,
                    )
                }
            ),
        )

        trader = CommodityTrader(state, {"GENERAL": {}}, {})
        orders = trader.get_orders()
        conversions = trader.get_conversions()

        self.assertIn(COMMODITY_SYMBOL, orders)
        self.assertIsInstance(orders[COMMODITY_SYMBOL], list)
        self.assertIsInstance(conversions, int)


if __name__ == "__main__":
    unittest.main()
