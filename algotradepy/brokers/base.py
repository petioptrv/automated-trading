from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict

from algotradepy.orders import AnOrder


class NoPaperTradeException(Exception):
    pass


class ABroker(ABC):
    f"""The Abstract Broker class defining the broker interface.

    Parameters
    ----------
    simulation : bool, default True
        If set to True, the broker instance will be set to paper-trading mode.
        If a given broker implementation does not support paper-trading, it
        must raise {NoPaperTradeException}.

    Notes
    -----
    This class is deliberately kept minial until the optimal API is established
    and adopted by the other brokers.
    """

    def __init__(
        self, simulation: bool = True,
    ):
        self._simulation = simulation

    @property
    @abstractmethod
    def acc_cash(self) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def datetime(self) -> datetime:
        """Server date and time."""
        raise NotImplementedError

    @abstractmethod
    def get_position(self, symbol: str, *args, **kwargs) -> float:
        """Request the currently held position for a given symbol.

        Parameters
        ----------
        symbol : str
            The symbol for which to request position value.
        Returns
        -------
        float
            The current position for the specified symbol.
        """
        raise NotImplementedError
