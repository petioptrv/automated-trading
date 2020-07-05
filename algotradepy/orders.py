from abc import ABC
from enum import Enum
from typing import Optional

from algotradepy.utils import ReprAble, Comparable


class OrderAction(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderState(Enum):
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    PENDING = "PENDING"
    INACTIVE = "INACTIVE"


class OrderStatus(ReprAble, Comparable):
    def __init__(
        self,
        state: OrderState,
        filled: float,
        remaining: float,
        ave_fill_price: float,
        order_id: Optional[int],
    ):
        super().__init__()
        self._order_id = order_id
        self._state = state
        self._filled = filled
        self._remaining = remaining
        self._ave_fill_price = ave_fill_price

    @property
    def order_id(self) -> int:
        return self._order_id

    @property
    def state(self):
        return self._state

    @property
    def filled(self):
        return self._filled

    @property
    def remaining(self):
        return self._remaining

    @property
    def ave_fill_price(self):
        return self._ave_fill_price


class AnOrder(ABC, ReprAble):
    def __init__(
        self,
        action: OrderAction,
        quantity: float,
        order_id: Optional[int] = None,
    ):
        super().__init__()
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


class TrailingStop(AnOrder):
    # TODO: test
    def __init__(
        self,
        action: OrderAction,
        quantity: float,
        stop_price: Optional[float] = None,
        trailing_percent: Optional[float] = None,
        order_id: Optional[int] = None,
    ):
        assert stop_price is not None or trailing_percent is not None

        super().__init__(
            order_id=order_id, action=action, quantity=quantity,
        )
        self._stop_price = stop_price
        self._trailing_percent = trailing_percent

    @property
    def stop_price(self):
        return self._stop_price

    @property
    def trailing_percent(self):
        return self._trailing_percent
