from enum import Enum
from typing import Optional

from algotradepy.contracts import AContract
from algotradepy.orders import AnOrder
from algotradepy.utils import ReprAble, Comparable


class TradeState(Enum):
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    PENDING = "PENDING"
    INACTIVE = "INACTIVE"


class TradeStatus(ReprAble, Comparable):
    """
    Semantically, associated with an order.
    """
    def __init__(
            self,
            state: TradeState,
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


class Trade:
    def __init__(
            self,
            contract: AContract,
            order: AnOrder,
            status: Optional[TradeStatus] = None,
    ):
        self._contract = contract
        self._order = order
        self._status = status

    @property
    def contract(self) -> AContract:
        return self._contract

    @property
    def order(self) -> AnOrder:
        return self._order

    @property
    def status(self) -> TradeStatus:
        return self._status
