from abc import ABC, abstractmethod
from datetime import date
from enum import Enum
from typing import Optional

from algotradepy.utils import ReprAble, Comparable


class Exchange(Enum):
    # North America
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    TSE = "TSE"
    VENTURE = "VENTURE"

    # Europe
    FWB = "FWB"
    IBIS = "IBIS"  # might be XETRA
    VSE = "VSE"
    LSE = "LSE"
    BATEUK = "BATEUK"

    # Asia/Pacific
    SEHK = "SEHK"
    ASX = "ASX"
    TSEJ = "TSEJ"


class Currency(Enum):
    USD = "USD"
    CAD = "CAD"
    EUR = "EUR"
    GBP = "GBP"
    AUD = "AUD"
    HKD = "HKD"
    JPY = "JPY"


class Right(Enum):
    CALL = "CALL"
    PUT = "PUT"


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

    @exchange.setter
    def exchange(self, ex: Exchange):
        assert isinstance(ex, Exchange)
        self._exchange = ex

    @property
    def currency(self) -> Currency:
        return self._currency

    @currency.setter
    def currency(self, cu: Currency):
        assert isinstance(cu, Currency)
        self._currency = cu


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
