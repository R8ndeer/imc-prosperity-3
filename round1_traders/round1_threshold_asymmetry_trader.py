from datamodel import Order, OrderDepth, TradingState
import json


PEPPER_ROOT = "INTARIAN_PEPPER_ROOT"
OSMIUM = "ASH_COATED_OSMIUM"

POSITION_LIMITS = {
    PEPPER_ROOT: 80,
    OSMIUM: 80,
}

# Pepper Root: keep the wall-mid anchor, but bias toward being longer by
# buying more readily and selling more selectively.
PEPPER_BUY_TAKE_THRESHOLD = 1
PEPPER_SELL_TAKE_THRESHOLD = 2
PEPPER_PASSIVE_SELL_OFFSET = 1


class BaseProductTrader:
    def __init__(self, symbol: str, state: TradingState):
        self.symbol = symbol
        self.state = state
        self.position_limit = POSITION_LIMITS[symbol]
        self.initial_position = state.position.get(symbol, 0)
        self.max_allowed_buy_volume = self.position_limit - self.initial_position
        self.max_allowed_sell_volume = self.position_limit + self.initial_position
        self.orders = []

        order_depth = state.order_depths.get(symbol, OrderDepth())
        self.buy_orders = {
            int(price): abs(int(volume))
            for price, volume in sorted(order_depth.buy_orders.items(), key=lambda item: item[0], reverse=True)
        }
        self.sell_orders = {
            int(price): abs(int(volume))
            for price, volume in sorted(order_depth.sell_orders.items(), key=lambda item: item[0])
        }
        self.best_bid = max(self.buy_orders) if self.buy_orders else None
        self.best_ask = min(self.sell_orders) if self.sell_orders else None
        self.bid_wall = max(self.buy_orders) if self.buy_orders else None
        self.ask_wall = min(self.sell_orders) if self.sell_orders else None
        self.wall_mid = (self.bid_wall + self.ask_wall) / 2 if self.bid_wall is not None and self.ask_wall is not None else None

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


class PepperRootTrader(BaseProductTrader):
    """
    Variant 1: threshold asymmetry.
    Keeps the baseline wall-mid fair value, but makes buying easier and selling
    more selective so the strategy carries a mild long bias.
    """

    def get_orders(self):
        if self.wall_mid is None or self.bid_wall is None or self.ask_wall is None:
            return {self.symbol: self.orders}

        for ask_price, ask_volume in self.sell_orders.items():
            if ask_price <= self.wall_mid - PEPPER_BUY_TAKE_THRESHOLD:
                self.bid(ask_price, ask_volume)
            elif ask_price <= self.wall_mid and self.initial_position < 0:
                self.bid(ask_price, min(ask_volume, abs(self.initial_position)))

        for bid_price, bid_volume in self.buy_orders.items():
            if bid_price >= self.wall_mid + PEPPER_SELL_TAKE_THRESHOLD and self.initial_position > 0:
                self.ask(bid_price, min(bid_volume, self.initial_position))

        bid_price = self.bid_wall + 1
        ask_price = max(self.ask_wall - 1, int(self.wall_mid + PEPPER_PASSIVE_SELL_OFFSET))

        for visible_bid, visible_volume in self.buy_orders.items():
            improved_price = visible_bid + 1
            if visible_volume > 1 and improved_price < self.wall_mid:
                bid_price = max(bid_price, improved_price)
                break
            if visible_bid < self.wall_mid:
                bid_price = max(bid_price, visible_bid)
                break

        for visible_ask, visible_volume in self.sell_orders.items():
            improved_price = visible_ask - 1
            if visible_volume > 1 and improved_price > self.wall_mid + PEPPER_PASSIVE_SELL_OFFSET:
                ask_price = min(ask_price, improved_price)
                break

        self.bid(bid_price, self.max_allowed_buy_volume)
        self.ask(ask_price, self.max_allowed_sell_volume)
        return {self.symbol: self.orders}


class OsmiumTrader(BaseProductTrader):
    """Keep Osmium close to the current working baseline for isolated comparison."""

    def get_orders(self):
        if self.wall_mid is None or self.bid_wall is None or self.ask_wall is None:
            return {self.symbol: self.orders}

        bid_price = self.bid_wall + 1
        ask_price = self.ask_wall - 1

        if bid_price >= self.wall_mid:
            bid_price = self.bid_wall
        if ask_price <= self.wall_mid:
            ask_price = self.ask_wall

        self.bid(bid_price, self.max_allowed_buy_volume)
        self.ask(ask_price, self.max_allowed_sell_volume)
        return {self.symbol: self.orders}


class Trader:
    def bid(self):
        return 0

    def run(self, state: TradingState):
        result = {}

        if PEPPER_ROOT in state.order_depths:
            result.update(PepperRootTrader(PEPPER_ROOT, state).get_orders())

        if OSMIUM in state.order_depths:
            result.update(OsmiumTrader(OSMIUM, state).get_orders())

        traderData = json.dumps({})
        conversions = 0
        return result, conversions, traderData
