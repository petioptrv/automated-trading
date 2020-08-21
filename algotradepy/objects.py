from typing import Optional

from algotradepy.contracts import Exchange, AContract
from algotradepy.utils import ReprAble, Comparable


class Tick(ReprAble, Comparable):
    def __init__(
        self,
        timestamp: float,
        symbol: str,
        price: float,
        size: float,
        exchange: Optional[Exchange] = None,
    ):
        self._timestamp = timestamp
        self._symbol = symbol
        self._price = price
        self._size = size
        self._exchange = exchange

    @property
    def timestamp(self) -> float:
        return self._timestamp

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def price(self) -> float:
        return self._price

    @property
    def size(self) -> float:
        return self._size

    @property
    def exchange(self) -> Exchange:
        return self._exchange


class Position(ReprAble, Comparable):
    def __init__(
        self,
        account: str,
        contract: AContract,
        position: float,
        ave_fill_price: float,
    ):
        ReprAble.__init__(self)
        self._account = account
        self._contract = contract
        self._position = position
        self._ave_fill_price = ave_fill_price

    @property
    def account(self) -> str:
        return self._account

    @property
    def contract(self) -> AContract:
        return self._contract

    @property
    def position(self) -> float:
        return self._position

    @property
    def ave_fill_price(self) -> float:
        return self._ave_fill_price


class Greeks(ReprAble, Comparable):
    def __init__(
        self, delta: float, gamma: float, vega: float, theta: float,
    ):
        self._delta = delta
        self._gamma = gamma
        self._vega = vega
        self._theta = theta

    @property
    def delta(self) -> float:
        return self._delta

    @property
    def gamma(self):
        return self._gamma

    @property
    def vega(self):
        return self._vega

    @property
    def theta(self):
        return self._theta
