from typing import Optional

from algotradepy.contracts import Exchange
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
