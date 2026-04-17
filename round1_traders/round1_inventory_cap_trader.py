from datamodel import Order, OrderDepth, TradingState
import json


PEPPER_ROOT = "INTARIAN_PEPPER_ROOT"
OSMIUM = "ASH_COATED_OSMIUM"

POSITION_LIMITS = {
    PEPPER_ROOT: 80,
    OSMIUM: 80,
}

# Pepper Root: accumulate long inventory gradually when short-term drift is
# positive, but keep inventory below a softer cap and unwind when signal weakens.
PEPPER_DRIFT_ALPHA = 0.30
PEPPER_ACCUMULATION_CAP = 40
PEPPER_ACCUMULATION_CLIP = 8
PEPPER_UNWIND_CLIP = 12
PEPPER_BUY_THRESHOLD = 1
PEPPER_RICH_EXIT_OFFSET = 2
PEPPER_HISTORY_KEY = "pepper_wall_mid_prev"


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
    Variant 3: inventory accumulation with cap.
    When drift is positive, Pepper Root can build a long inventory gradually up
    to a soft cap. It unwinds when drift turns weak/negative or price gets rich.
    """

    def __init__(self, state: TradingState, trader_state: dict):
        super().__init__(PEPPER_ROOT, state)
        self.trader_state = trader_state

    def get_orders(self):
        if self.wall_mid is None or self.bid_wall is None or self.ask_wall is None:
            return {self.symbol: self.orders}

        prev_mid = self.trader_state.get(PEPPER_HISTORY_KEY)
        drift = 0.0 if prev_mid is None else self.wall_mid - float(prev_mid)
        adjusted_fair = self.wall_mid + PEPPER_DRIFT_ALPHA * drift
        self.trader_state[PEPPER_HISTORY_KEY] = self.wall_mid

        if drift > 0 and self.initial_position < PEPPER_ACCUMULATION_CAP:
            accumulation_room = PEPPER_ACCUMULATION_CAP - self.initial_position
            buy_size = min(PEPPER_ACCUMULATION_CLIP, accumulation_room)

            if self.best_ask is not None and self.best_ask <= adjusted_fair + PEPPER_BUY_THRESHOLD:
                self.bid(self.best_ask, buy_size)
            else:
                self.bid(self.bid_wall + 1, buy_size)

        for ask_price, ask_volume in self.sell_orders.items():
            if ask_price <= adjusted_fair - PEPPER_BUY_THRESHOLD:
                self.bid(ask_price, min(ask_volume, PEPPER_ACCUMULATION_CLIP))

        should_unwind = drift <= 0 or (self.best_bid is not None and self.best_bid >= adjusted_fair + PEPPER_RICH_EXIT_OFFSET)
        if should_unwind and self.initial_position > 0:
            unwind_size = min(self.initial_position, PEPPER_UNWIND_CLIP)
            sell_price = self.best_bid if self.best_bid is not None else self.bid_wall
            if sell_price is not None:
                self.ask(sell_price, unwind_size)

        if self.initial_position <= 0:
            ask_price = max(self.ask_wall - 1, int(adjusted_fair + 1))
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
        try:
            trader_state = json.loads(state.traderData) if state.traderData else {}
            if not isinstance(trader_state, dict):
                trader_state = {}
        except Exception:
            trader_state = {}

        if PEPPER_ROOT in state.order_depths:
            result.update(PepperRootTrader(state, trader_state).get_orders())

        if OSMIUM in state.order_depths:
            result.update(OsmiumTrader(OSMIUM, state).get_orders())

        traderData = json.dumps(trader_state)
        conversions = 0
        return result, conversions, traderData
