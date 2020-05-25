from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Callable, Optional


class ABroker(ABC):
    def __init__(
            self,
            simulation: bool = True,
    ):
        self._simulation = simulation

    @property
    @abstractmethod
    def acc_cash(self) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def datetime(self) -> datetime:
        raise NotImplementedError

    @abstractmethod
    def subscribe_for_bars(
            self,
            symbol: str,
            bar_size: timedelta,
            func: Callable,
            fn_kwargs: Optional[dict] = None,
    ):
        raise NotImplementedError

    @abstractmethod
    def get_position(self, symbol: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def buy(self, symbol: str, n_shares: int, *args, **kwargs) -> bool:
        raise NotImplementedError

    @abstractmethod
    def sell(self, symbol: str, n_shares: int, *args, **kwargs) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_transaction_fee(self) -> float:
        raise NotImplementedError
