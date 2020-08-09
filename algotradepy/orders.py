from abc import ABC
from enum import Enum
from typing import Optional, List

from algotradepy.order_conditions import ACondition
from algotradepy.utils import ReprAble


class OrderAction(Enum):
    """The available order actions.

    Values
    ------
    * BUY
    * SELL
    """

    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(Enum):
    """The order time-in-force options.

    Values
    ------
    * DAY
    * GTC
    """

    DAY = "DAY"
    GTC = "GTC"


class AnOrder(ABC, ReprAble):
    """The abstract order class defining the basic order properties.

    Parameters
    ----------
    action : ~algotradepy.orders.OrderAction
        The order action.
    quantity : float
        The order size.
    order_id : int, optional, default None
        The order ID.
    time_in_force : ~algotradepy.orders.TimeInForce, optional, default None
        Time-in-force option.
    conditions : list of ~algotradepy.orders.ACondition, optional, default None
        A list of conditions attached to the order.
    parent_id : int, optional, default None
        The parent order's ID.
    """

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
    """A market order definition."""

    def __init__(
        self,
        action: OrderAction,
        quantity: float,
        order_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            order_id=order_id, action=action, quantity=quantity, **kwargs
        )


class LimitOrder(AnOrder):
    """A limit order definition.

    Parameters
    ----------
    action
    quantity
    limit_price : float
        The limit price for this order.
    order_id
    kwargs
    """

    def __init__(
        self,
        action: OrderAction,
        quantity: float,
        limit_price: float,
        order_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            order_id=order_id, action=action, quantity=quantity, **kwargs
        )
        self._limit_price = limit_price

    @property
    def limit_price(self) -> float:
        return self._limit_price


class TrailingStopOrder(AnOrder):
    """A trailing stop order definition.

    Parameters
    ----------
    action
    quantity
    trail_stop_price : float, optional, default None
        The Trailing stop price for this order.
    aux_price : float, optional, default None
        Can be specified instead of `trail_percent`, in which case the order is
        executed at `aux_price` away from `trailing_stop_price`. Must be
        provided if `trail_percent` is left blank.
    trail_percent : float, optional, default None
        The percentage offset from `trail_stop_price` at which to execute.
        Must be provided if `aux_price` is not set.
    order_id
    kwargs
    """

    def __init__(
        self,
        action: OrderAction,
        quantity: float,
        trail_stop_price: Optional[float] = None,
        aux_price: Optional[float] = None,
        trail_percent: Optional[float] = None,
        order_id: Optional[int] = None,
        **kwargs,
    ):
        self._validate(
            aux_price=aux_price, trail_percent=trail_percent,
        )
        super().__init__(
            order_id=order_id, action=action, quantity=quantity, **kwargs
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
