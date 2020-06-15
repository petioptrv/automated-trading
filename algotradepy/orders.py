from abc import ABC
from enum import Enum
from typing import Dict, Optional


class OrderAction(Enum):
    BUY = 0
    SELL = 1


class OrderStatus:
    def __init__(
        self,
        status: str,
        filled: float,
        remaining: float,
        ave_fill_price: float,
        order_id: Optional[int],
    ):
        self._order_id = order_id
        self._status = status
        self._filled = filled
        self._remaining = remaining
        self._ave_fill_price = ave_fill_price

    @property
    def order_id(self) -> int:
        return self._order_id

    @property
    def status(self):
        return self._status

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
        action: OrderAction,
        quantity: float,
        order_id: Optional[int] = None,
    ):
        self._order_id = order_id
        self._action = action
        self._quantity = quantity

    @property
    def order_id(self) -> int:
        return self._order_id

    @property
    def action(self) -> OrderAction:
        return self._action

    @property
    def quantity(self) -> float:
        return self._quantity


class MarketOrder(AnOrder):
    def __init__(
        self,
        action: OrderAction,
        quantity: float,
        order_id: Optional[int] = None,
    ):
        super().__init__(
            order_id=order_id, action=action, quantity=quantity,
        )


class LimitOrder(AnOrder):
    def __init__(
        self,
        action: OrderAction,
        quantity: float,
        limit_price: float,
        order_id: Optional[int] = None,
    ):
        super().__init__(
            order_id=order_id, action=action, quantity=quantity,
        )
        self._limit_price = limit_price

    @property
    def limit_price(self) -> float:
        return self._limit_price
