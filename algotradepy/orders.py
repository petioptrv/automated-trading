from abc import ABC
from enum import Enum
from typing import Optional, List

from algotradepy.order_conditions import ACondition
from algotradepy.utils import ReprAble


class OrderAction(Enum):
    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(Enum):
    DAY = "DAY"
    GTC = "GTC"


class AnOrder(ABC, ReprAble):
    def __init__(
        self,
        action: OrderAction,
        quantity: float,
        order_id: Optional[int] = None,
        time_in_force: Optional[TimeInForce] = None,
        conditions: Optional[List[ACondition]] = None,
        parent_id: Optional[int] = None,
    ):
        super().__init__()
        self._order_id = order_id
        self._action = action
        self._quantity = quantity
        self._time_in_force = time_in_force
        if conditions is None:
            conditions = []
        self._conditions = conditions
        self._parent_id = parent_id

    @property
    def order_id(self) -> int:
        return self._order_id

    @property
    def action(self) -> OrderAction:
        return self._action

    @property
    def quantity(self) -> float:
        return self._quantity

    @property
    def time_in_force(self) -> TimeInForce:
        return self._time_in_force

    @property
    def conditions(self) -> List[ACondition]:
        return self._conditions

    @property
    def parent_id(self):
        return self._parent_id


class MarketOrder(AnOrder):
    def __init__(
        self,
        action: OrderAction,
        quantity: float,
        order_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            order_id=order_id,
            action=action,
            quantity=quantity,
            **kwargs
        )


class LimitOrder(AnOrder):
    def __init__(
        self,
        action: OrderAction,
        quantity: float,
        limit_price: float,
        order_id: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            order_id=order_id,
            action=action,
            quantity=quantity,
            **kwargs
        )
        self._limit_price = limit_price

    @property
    def limit_price(self) -> float:
        return self._limit_price


class TrailingStopOrder(AnOrder):
    # TODO: document
    def __init__(
        self,
        action: OrderAction,
        quantity: float,
        trail_stop_price: Optional[float] = None,
        aux_price: Optional[float] = None,
        trail_percent: Optional[float] = None,
        order_id: Optional[int] = None,
        **kwargs
    ):
        self._validate(
            aux_price=aux_price, trail_percent=trail_percent,
        )
        super().__init__(
            order_id=order_id,
            action=action,
            quantity=quantity,
            **kwargs
        )
        self._trail_stop_price = trail_stop_price
        self._trail_percent = trail_percent
        self._aux_price = aux_price

    @property
    def trail_stop_price(self) -> Optional[float]:
        return self._trail_stop_price

    @property
    def trail_percent(self) -> Optional[float]:
        return self._trail_percent

    @property
    def aux_price(self):
        return self._aux_price

    @staticmethod
    def _validate(
            aux_price: Optional[float], trail_percent: Optional[float],
    ):
        if (trail_percent is None) == (aux_price is None):
            raise ValueError(
                f"Exactly one of aux_price or trail_percent must be specified"
                f" for {TrailingStopOrder.__name__}."
            )
