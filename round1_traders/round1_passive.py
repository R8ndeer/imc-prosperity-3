from __future__ import annotations

import json
from dataclasses import dataclass

from datamodel import Order, OrderDepth, TradingState


PEPPER_ROOT = "INTARIAN_PEPPER_ROOT"
OSMIUM = "ASH_COATED_OSMIUM"

POSITION_LIMITS = {
    PEPPER_ROOT: 80,
    OSMIUM: 80,
}


@dataclass
class ProductBook:
    buy_orders: dict[int, int]
    sell_orders: dict[int, int]
    best_bid: int | None
    best_ask: int | None
    wall_mid: float | None


class BaseProductTrader:
    def __init__(self, symbol: str, state: TradingState):
        self.symbol = symbol
        self.state = state
        self.position_limit = POSITION_LIMITS[symbol]
        self.initial_position = state.position.get(symbol, 0)

        self.max_allowed_buy_volume = self.position_limit - self.initial_position
        self.max_allowed_sell_volume = self.position_limit + self.initial_position

        self.orders: list[Order] = []
        self.book = self._build_book()

    def _build_book(self) -> ProductBook:
        order_depth = self.state.order_depths.get(self.symbol, OrderDepth())

        buy_orders = {
            int(price): abs(int(volume))
            for price, volume in sorted(
                order_depth.buy_orders.items(),
                key=lambda item: item[0],
                reverse=True,
            )
        }
        sell_orders = {
            int(price): abs(int(volume))
            for price, volume in sorted(
                order_depth.sell_orders.items(),
                key=lambda item: item[0],
            )
        }

        best_bid = max(buy_orders) if buy_orders else None
        best_ask = min(sell_orders) if sell_orders else None
        wall_mid = (
            (best_bid + best_ask) / 2
            if best_bid is not None and best_ask is not None
            else None
        )

        return ProductBook(
            buy_orders=buy_orders,
            sell_orders=sell_orders,
            best_bid=best_bid,
            best_ask=best_ask,
            wall_mid=wall_mid,
        )

    def bid(self, price: int, volume: int) -> None:
        volume = min(abs(int(volume)), self.max_allowed_buy_volume)
        if volume <= 0:
            return
        self.orders.append(Order(self.symbol, int(price), volume))
        self.max_allowed_buy_volume -= volume

    def ask(self, price: int, volume: int) -> None:
        volume = min(abs(int(volume)), self.max_allowed_sell_volume)
        if volume <= 0:
            return
        self.orders.append(Order(self.symbol, int(price), -volume))
        self.max_allowed_sell_volume -= volume

    def get_orders(self) -> dict[str, list[Order]]:
        raise NotImplementedError


class PepperRootKelpStyleTrader(BaseProductTrader):
    """
    Kelp-style trader with the informed-agent logic removed.

    This is the closest direct adaptation of Frankfurt Hedgehogs'
    DynamicTrader to Pepper Root, but without Olivia detection.
    """

    def __init__(self, state: TradingState):
        super().__init__(PEPPER_ROOT, state)

    def get_orders(self) -> dict[str, list[Order]]:
        if (
            self.book.wall_mid is None
            or self.book.best_bid is None
            or self.book.best_ask is None
        ):
            return {self.symbol: self.orders}

        # Start by improving each side of the current book by 1 tick.
        bid_price = self.book.best_bid + 1
        ask_price = self.book.best_ask - 1

        # Safety checks so we do not cross through the midpoint.
        if bid_price >= self.book.wall_mid:
            bid_price = self.book.best_bid

        if ask_price <= self.book.wall_mid:
            ask_price = self.book.best_ask

        # Quote full available size on both sides.
        self.bid(bid_price, self.max_allowed_buy_volume)
        self.ask(ask_price, self.max_allowed_sell_volume)

        return {self.symbol: self.orders}


class OsmiumTrader(BaseProductTrader):
    """
    Keep Osmium on the simple symmetric quoting baseline.
    """

    def __init__(self, state: TradingState):
        super().__init__(OSMIUM, state)

    def get_orders(self) -> dict[str, list[Order]]:
        if (
            self.book.wall_mid is None
            or self.book.best_bid is None
            or self.book.best_ask is None
        ):
            return {self.symbol: self.orders}

        bid_price = self.book.best_bid + 1
        ask_price = self.book.best_ask - 1

        if bid_price >= self.book.wall_mid:
            bid_price = self.book.best_bid

        if ask_price <= self.book.wall_mid:
            ask_price = self.book.best_ask

        self.bid(bid_price, self.max_allowed_buy_volume)
        self.ask(ask_price, self.max_allowed_sell_volume)

        return {self.symbol: self.orders}


class Trader:
    PRODUCT_TRADERS = {
        PEPPER_ROOT: PepperRootKelpStyleTrader,
        OSMIUM: OsmiumTrader,
    }

    def bid(self) -> int:
        # Harmless for rounds where bid() is ignored.
        return 0

    def run(self, state: TradingState):
        result: dict[str, list[Order]] = {}
        trader_data = {}

        for product, trader_cls in self.PRODUCT_TRADERS.items():
            if product not in state.order_depths:
                continue

            trader = trader_cls(state)
            result.update(trader.get_orders())

        return result, 0, json.dumps(trader_data)
