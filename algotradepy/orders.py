from abc import ABC
from enum import Enum


class OrderAction(Enum):
    BUY = 0
    SELL = 1


class SecType(Enum):
    STK = 0


class OrderStatus:
    def __init__(
        self,
        order_id: int,
        filled: float,
        remaining: float,
        ave_fill_price: float,
    ):
        self._order_id = order_id
        self._filled = filled
        self._remaining = remaining
        self._ave_fill_price = ave_fill_price

    @property
    def order_id(self) -> int:
        return self._order_id

    @property
    def filled(self):
        return self._filled

    @property
    def remaining(self):
        return self._remaining

    @property
    def ave_fill_price(self):
        return self._ave_fill_price


class AnOrder(ABC):
    def __init__(
        self,
        order_id: int,
        symbol: str,
        action: OrderAction,
        quantity: float,
        sec_type: SecType,
    ):
        self._order_id = order_id
        self._symbol = symbol
        self._action = action
        self._quantity = quantity
        self._sec_type = sec_type

    @property
    def order_id(self) -> int:
        return self._order_id

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def action(self) -> OrderAction:
        return self._action

    @property
    def quantity(self) -> float:
        return self._quantity

    @property
    def sec_type(self) -> SecType:
        return self._sec_type


class MarketOrder(AnOrder):
    def __init__(
        self,
        order_id: int,
        symbol: str,
        action: OrderAction,
        quantity: float,
        sec_type: SecType,
    ):
        super().__init__(
            order_id=order_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            sec_type=sec_type,
        )


class LimitOrder(AnOrder):
    def __init__(
        self,
        order_id: int,
        symbol: str,
        action: OrderAction,
        quantity: float,
        sec_type: SecType,
        limit_price: float,
    ):
        super().__init__(
            order_id=order_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            sec_type=sec_type,
        )
        self._limit_price = limit_price

    @property
    def limit_price(self) -> float:
        return self._limit_price
