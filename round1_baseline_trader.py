from __future__ import annotations

import json
from dataclasses import dataclass

from datamodel import Order, OrderDepth, TradingState


PEPPER_ROOT = "INTARIAN_PEPPER_ROOT"
OSMIUM = "ASH_COATED_OSMIUM"

ROUND1_PRODUCTS = [PEPPER_ROOT, OSMIUM]
POSITION_LIMITS = {
    PEPPER_ROOT: 80,
    OSMIUM: 80,
}


def get_book_walls(order_depth: OrderDepth) -> tuple[int | None, float | None, int | None]:
    buy_orders = order_depth.buy_orders if order_depth is not None else {}
    sell_orders = order_depth.sell_orders if order_depth is not None else {}

    bid_wall = min(buy_orders) if buy_orders else None
    ask_wall = max(sell_orders) if sell_orders else None
    wall_mid = (bid_wall + ask_wall) / 2 if bid_wall is not None and ask_wall is not None else None
    return bid_wall, wall_mid, ask_wall


@dataclass
class ProductBook:
    buy_orders: dict[int, int]
    sell_orders: dict[int, int]
    bid_wall: int | None
    wall_mid: float | None
    ask_wall: int | None
    best_bid: int | None
    best_ask: int | None


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
            for price, volume in sorted(order_depth.buy_orders.items(), key=lambda item: item[0], reverse=True)
        }
        sell_orders = {
            int(price): abs(int(volume))
            for price, volume in sorted(order_depth.sell_orders.items(), key=lambda item: item[0])
        }

        bid_wall, wall_mid, ask_wall = get_book_walls(OrderDepth(buy_orders=buy_orders, sell_orders=sell_orders))
        best_bid = max(buy_orders) if buy_orders else None
        best_ask = min(sell_orders) if sell_orders else None

        return ProductBook(
            buy_orders=buy_orders,
            sell_orders=sell_orders,
            bid_wall=bid_wall,
            wall_mid=wall_mid,
            ask_wall=ask_wall,
            best_bid=best_bid,
            best_ask=best_ask,
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


class PepperRootTrader(BaseProductTrader):
    """
    Adapted from the old stable-product Round 1 baseline.
    It uses the visible book walls as a fair-value proxy, takes clearly favorable
    prices first, then posts improved passive quotes inside the visible spread.
    """

    def __init__(self, state: TradingState):
        super().__init__(PEPPER_ROOT, state)

    def get_orders(self) -> dict[str, list[Order]]:
        if self.book.wall_mid is None or self.book.bid_wall is None or self.book.ask_wall is None:
            return {self.symbol: self.orders}

        for ask_price, ask_volume in self.book.sell_orders.items():
            if ask_price <= self.book.wall_mid - 1:
                self.bid(ask_price, ask_volume)
            elif ask_price <= self.book.wall_mid and self.initial_position < 0:
                self.bid(ask_price, min(ask_volume, abs(self.initial_position)))

        for bid_price, bid_volume in self.book.buy_orders.items():
            if bid_price >= self.book.wall_mid + 1:
                self.ask(bid_price, bid_volume)
            elif bid_price >= self.book.wall_mid and self.initial_position > 0:
                self.ask(bid_price, min(bid_volume, self.initial_position))

        bid_price = int(self.book.bid_wall + 1)
        ask_price = int(self.book.ask_wall - 1)

        for visible_bid, visible_volume in self.book.buy_orders.items():
            improved_price = visible_bid + 1
            if visible_volume > 1 and improved_price < self.book.wall_mid:
                bid_price = max(bid_price, improved_price)
                break
            if visible_bid < self.book.wall_mid:
                bid_price = max(bid_price, visible_bid)
                break

        for visible_ask, visible_volume in self.book.sell_orders.items():
            improved_price = visible_ask - 1
            if visible_volume > 1 and improved_price > self.book.wall_mid:
                ask_price = min(ask_price, improved_price)
                break
            if visible_ask > self.book.wall_mid:
                ask_price = min(ask_price, visible_ask)
                break

        self.bid(bid_price, self.max_allowed_buy_volume)
        self.ask(ask_price, self.max_allowed_sell_volume)
        return {self.symbol: self.orders}


class OsmiumTrader(BaseProductTrader):
    """
    Simplified adaptation of the old dynamic Round 1 baseline.
    Legacy informed-flow behavior is intentionally removed for the first-pass
    baseline, leaving only symmetric quoting around the visible book walls.
    """

    def __init__(self, state: TradingState):
        super().__init__(OSMIUM, state)

    def get_orders(self) -> dict[str, list[Order]]:
        if self.book.wall_mid is None or self.book.bid_wall is None or self.book.ask_wall is None:
            return {self.symbol: self.orders}

        bid_price = int(self.book.bid_wall + 1)
        ask_price = int(self.book.ask_wall - 1)

        if bid_price >= self.book.wall_mid:
            bid_price = int(self.book.bid_wall)
        if ask_price <= self.book.wall_mid:
            ask_price = int(self.book.ask_wall)

        self.bid(bid_price, self.max_allowed_buy_volume)
        self.ask(ask_price, self.max_allowed_sell_volume)
        return {self.symbol: self.orders}


class Trader:
    """
    Round 1-only baseline entrypoint for this year's products.
    This file is intentionally lean so it can be used both for local research
    replay and as a submission-oriented baseline.
    """

    PRODUCT_TRADERS = {
        PEPPER_ROOT: PepperRootTrader,
        OSMIUM: OsmiumTrader,
    }

    def run(self, state: TradingState):
        result: dict[str, list[Order]] = {}
        trader_data = {}

        for product, trader_cls in self.PRODUCT_TRADERS.items():
            if product not in state.order_depths:
                continue

            trader = trader_cls(state)
            result.update(trader.get_orders())

        return result, 0, json.dumps(trader_data)
