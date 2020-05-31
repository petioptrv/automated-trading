from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict


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
    def subscribe_to_bars(
        self,
        symbol: str,
        bar_size: timedelta,
        func: Callable,
        fn_kwargs: Optional[Dict] = None,
    ):
        """Subscribe to receiving historical bar data.

        The bars are fed back as pandas.Series objects.

        Parameters
        ----------
        symbol : str
            The symbol for which to request historical data.
        bar_size : timedelta
            The bar size to request.
        func : Callable
            The function to which to feed the bars.
        fn_kwargs : Dict
            Keyword arguments to feed to the callback function along with the
            bars.
        """
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

    @abstractmethod
    def buy(self, symbol: str, n_shares: float, *args, **kwargs) -> bool:
        """Submit a buy order.

        Parameters
        ----------
        symbol : str
            The symbol for which to submit a buy order.
        n_shares : float
            The number of shares to buy.
        """
        raise NotImplementedError

    @abstractmethod
    def sell(self, symbol: str, n_shares: float, *args, **kwargs) -> bool:
        """Submit a sell order.

        Parameters
        ----------
        symbol :
            The symbol for which to submit a sell order.
        n_shares : float
            The number of shares to sell
        """
        raise NotImplementedError

    @abstractmethod
    def get_transaction_fee(self) -> float:
        """Request the broker transaction cost.

        Returns
        -------
        float
            The cost per transaction.
        """
        raise NotImplementedError
