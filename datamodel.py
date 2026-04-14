from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Order:
    symbol: str
    price: int
    quantity: int


@dataclass
class OrderDepth:
    buy_orders: dict[int, int] = field(default_factory=dict)
    sell_orders: dict[int, int] = field(default_factory=dict)


@dataclass
class Trade:
    symbol: str
    price: int
    quantity: int
    buyer: str | None = None
    seller: str | None = None
    timestamp: int = 0


@dataclass
class ConversionObservation:
    bidPrice: float
    askPrice: float
    transportFees: float
    exportTariff: float
    importTariff: float
    sunlightIndex: float
    sugarPrice: float


@dataclass
class Observations:
    conversionObservations: dict[str, ConversionObservation] = field(default_factory=dict)


@dataclass
class TradingState:
    timestamp: int
    traderData: str
    position: dict[str, int] = field(default_factory=dict)
    order_depths: dict[str, OrderDepth] = field(default_factory=dict)
    market_trades: dict[str, list[Trade]] = field(default_factory=dict)
    own_trades: dict[str, list[Trade]] = field(default_factory=dict)
    observations: Observations = field(default_factory=Observations)
