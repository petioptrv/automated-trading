from abc import ABC, abstractmethod
from datetime import date
from enum import Enum
from typing import Optional

from algotradepy.utils import ReprAble, Comparable


class SecType(Enum):
    STK = 0
    OPT = 1


class Exchange(Enum):
    SMART = 0


class Currency(Enum):
    USD = 0


class Right(Enum):
    CALL = 0
    PUT = 1


class AContract(ABC, ReprAble, Comparable):
    def __init__(
        self,
        symbol: str,
        con_id: Optional[int] = None,
        exchange: Optional[Exchange] = None,
        currency: Currency = Currency.USD,
    ):
        super().__init__()
        self._con_id = con_id
        self._symbol = symbol
        self._exchange = exchange
        self._currency = currency

    @property
    def con_id(self) -> Optional[int]:
        return self._con_id

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def exchange(self) -> Optional[Exchange]:
        return self._exchange

    @property
    def currency(self) -> Currency:
        return self._currency


class StockContract(AContract):
    def __init__(
        self,
        symbol: str,
        con_id: Optional[int] = None,
        exchange: Optional[Exchange] = None,
        currency: Currency = Currency.USD,
    ):
        super().__init__(
            con_id=con_id, symbol=symbol, exchange=exchange, currency=currency,
        )


class OptionContract(AContract):
    def __init__(
        self,
        symbol: str,
        strike: float,
        right: Right,
        multiplier: float,
        last_trade_date: date,
        con_id: Optional[int] = None,
        exchange: Optional[Exchange] = None,
        currency: Currency = Currency.USD,
    ):
        super().__init__(
            con_id=con_id, symbol=symbol, exchange=exchange, currency=currency
        )
        self._strike = strike
        self._right = right
        self._multiplier = multiplier
        self._last_trade_date = last_trade_date

    @property
    def strike(self) -> float:
        return self._strike

    @property
    def right(self) -> Right:
        return self._right

    @property
    def multiplier(self) -> float:
        return self._multiplier

    @property
    def last_trade_date(self) -> date:
        return self._last_trade_date
