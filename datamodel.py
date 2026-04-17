from __future__ import annotations

import json
from dataclasses import dataclass, field
from json import JSONEncoder
from typing import Any


Time = int
Symbol = str
Product = str
Position = int
UserId = str
ObservationValue = int


@dataclass
class Listing:
    symbol: Symbol
    product: Product
    denomination: Product


@dataclass
class ConversionObservation:
    bidPrice: float
    askPrice: float
    transportFees: float
    exportTariff: float
    importTariff: float
    sunlight: float | None = None
    humidity: float | None = None
    # The Prosperity 4 wiki snippet is internally inconsistent here: the
    # constructor shows `sunlight`/`humidity`, while the body assigns
    # `sunlightIndex`/`sugarPrice`. We keep the official-looking constructor
    # shape, but expose both naming schemes explicitly for local compatibility.
    sunlightIndex: float | None = None
    sugarPrice: float | None = None

    def __post_init__(self) -> None:
        if self.sunlightIndex is None:
            self.sunlightIndex = self.sunlight
        if self.sunlight is None:
            self.sunlight = self.sunlightIndex
        if self.sugarPrice is None:
            self.sugarPrice = self.humidity
        if self.humidity is None:
            self.humidity = self.sugarPrice


@dataclass
class Observation:
    plainValueObservations: dict[Product, ObservationValue] = field(default_factory=dict)
    conversionObservations: dict[Product, ConversionObservation] = field(default_factory=dict)

    def __str__(self) -> str:
        return (
            "(plainValueObservations: "
            + json.dumps(self.plainValueObservations, sort_keys=True)
            + ", conversionObservations: "
            + json.dumps(self.conversionObservations, cls=ProsperityEncoder, sort_keys=True)
            + ")"
        )


Observations = Observation


@dataclass
class Order:
    symbol: Symbol
    price: int
    quantity: int

    def __str__(self) -> str:
        return f"({self.symbol}, {self.price}, {self.quantity})"

    def __repr__(self) -> str:
        return str(self)


@dataclass
class OrderDepth:
    buy_orders: dict[int, int] = field(default_factory=dict)
    sell_orders: dict[int, int] = field(default_factory=dict)


@dataclass
class Trade:
    symbol: Symbol
    price: int
    quantity: int
    buyer: UserId | None = None
    seller: UserId | None = None
    timestamp: int = 0

    def __str__(self) -> str:
        buyer = self.buyer if self.buyer is not None else ""
        seller = self.seller if self.seller is not None else ""
        return f"({self.symbol}, {buyer} << {seller}, {self.price}, {self.quantity}, {self.timestamp})"

    def __repr__(self) -> str:
        return str(self)


@dataclass
class TradingState:
    traderData: str
    timestamp: Time
    listings: dict[Symbol, Listing] = field(default_factory=dict)
    order_depths: dict[Symbol, OrderDepth] = field(default_factory=dict)
    own_trades: dict[Symbol, list[Trade]] = field(default_factory=dict)
    market_trades: dict[Symbol, list[Trade]] = field(default_factory=dict)
    position: dict[Product, Position] = field(default_factory=dict)
    observations: Observation = field(default_factory=Observation)

    def toJSON(self) -> str:
        return json.dumps(self, cls=ProsperityEncoder, sort_keys=True)

    def __repr__(self) -> str:
        return self.toJSON()


class ProsperityEncoder(JSONEncoder):
    def default(self, o: Any):
        if hasattr(o, "__dict__"):
            return o.__dict__
        return JSONEncoder.default(self, o)
