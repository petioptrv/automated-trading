from enum import Enum
from typing import Optional

from algotradepy.contracts import AContract
from algotradepy.orders import AnOrder
from algotradepy.utils import ReprAble, Comparable


class TradeState(Enum):
    """The possible trade states.

    Values
    ------
    * SUBMITTED
    * FILLED
    * CANCELLED
    * PENDING
    * INACTIVE
    """

    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    PENDING = "PENDING"
    INACTIVE = "INACTIVE"


class TradeStatus(ReprAble, Comparable):
    """Defines the status of an order.

    Parameters
    ----------
    state : ~algotradepy.trade.TradeState
        The state of the order.
    filled : float
        How much of the order was filled. Cannot exceed the order size.
    remaining : float
        How much of the order is remaining.
    ave_fill_price : float
        The average price at which the order was filled.
    order_id : int, optional, default None
        The associated order's ID.
    """

    def __init__(
        self,
        state: TradeState,
        filled: float,
        remaining: float,
        ave_fill_price: float,
        order_id: Optional[int] = None,
    ):
        ReprAble.__init__(self)
        Comparable.__init__(self)
        self._order_id = order_id
        self._state = state
        self._filled = filled
        self._remaining = remaining
        self._ave_fill_price = ave_fill_price

    @property
    def order_id(self) -> int:
        return self._order_id

    @property
    def state(self) -> TradeState:
        return self._state

    @property
    def filled(self) -> float:
        return self._filled

    @property
    def remaining(self) -> float:
        return self._remaining

    @property
    def ave_fill_price(self) -> float:
        return self._ave_fill_price


class Trade(ReprAble):
    """This class defines a trade.

    Parameters
    ----------
    contract : ~algotradepy.contracts.AContract
        The contract definition for this trade.
    order : ~algotradepy.orders.AnOrder
        The order definition for this trade.
    status : ~algotradepy.trade.TradeStatus, optional, default None
        The status of the trade.
    """

    def __init__(
        self,
        contract: AContract,
        order: AnOrder,
        status: Optional[TradeStatus] = None,
    ):
        super().__init__()
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

    @status.setter
    def status(self, new_status: TradeStatus):
        self._status = new_status

    def __hash__(self):
        h = hash((hash(self._contract), hash(self._order)),)
        return h

    def __eq__(self, other) -> bool:
        equal = True

        if not isinstance(other, Trade):
            equal = False
        elif self.contract != other.contract or self.order != other.order:
            equal = False

        return equal
