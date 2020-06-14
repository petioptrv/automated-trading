from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional


class SecType(Enum):
    STK = 0
    OPT = 1


class Exchange(Enum):
    SMART = 0


class Currency(Enum):
    USD = 0


class AContract(ABC):
    def __init__(
        self,
        symbol: str,
        con_id: Optional[int] = None,
        exchange: Optional[Exchange] = None,
        currency: Currency = Currency.USD,
    ):
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


class STKContract(AContract):
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


class OPTContract(AContract):
    def __init__(
        self,
        symbol: str,
        strike: float = 0.0,
        right: str = "",
        multiplier: str = "",
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

    @property
    def strike(self):
        return self._strike

    @property
    def right(self):
        return self._right

    @property
    def multiplier(self):
        return self._multiplier
