from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable, Optional, Dict, Tuple, List

from algotradepy.contracts import AContract
from algotradepy.trade import Trade


class NoPaperTradeException(Exception):
    pass


class ABroker(ABC):
    """The Abstract Broker class defining the broker interface.

    Parameters
    ----------
    simulation : bool, default True
        If set to True, the broker instance will be set to paper-trading mode.
        If a given broker implementation does not support paper-trading, it
        must raise `NoPaperTradeException`.

    Notes
    -----
    This class is deliberately kept minial until the optimal API is established
    and adopted by the other brokers.
    """

    def __init__(self, *args, simulation: bool = True, **kwargs):
        self._simulation = simulation

    @property
    @abstractmethod
    def acc_cash(self) -> float:
        """The total funds available across all accounts."""
        raise NotImplementedError

    @property
    @abstractmethod
    def datetime(self) -> datetime:
        """Server date and time."""
        raise NotImplementedError

    @property
    @abstractmethod
    def trades(self) -> List[Trade]:
        """Returns all trades placed in the current session."""
        raise NotImplementedError

    @property
    @abstractmethod
    def open_trades(self) -> List[Trade]:
        """Returns all currently open trades placed in the ongoing session."""
        raise NotImplementedError

    @abstractmethod
    def sleep(self, secs: float):
        """Allows the server to deliver data."""
        raise NotImplementedError

    @abstractmethod
    def subscribe_to_new_trades(
        self, func: Callable, fn_kwargs: Optional[Dict] = None,
    ):
        """Subscribe to being notified of all newly created orders.

        The orders are transmitted only if they were successfully submitted.

        Parameters
        ----------
        func : Callable
            The function to which to feed the bars. It must accept
            :class:`~algotradepy.contracts.AContract` and
            :class:`~algotradepy.orders.AnOrder` as its sole positional
            arguments.
        fn_kwargs : Dict
            Keyword arguments to feed to the callback function along with the
            bars.
        """
        raise NotImplementedError

    @abstractmethod
    def subscribe_to_trade_updates(
        self, func: Callable, fn_kwargs: Optional[Dict] = None,
    ):
        """Subscribe to receiving updates on orders' status.

        Parameters
        ----------
        func : Callable
            The callback function. It must accept a
            :class:`~algotradepy.trade.TradeStatus` as its sole positional
            argument.
        fn_kwargs : dict
            The keyword arguments to pass to the callback function along with
            the positional arguments.
        """
        raise NotImplementedError

    @abstractmethod
    def place_trade(self, trade: Trade, *args, **kwargs) -> Tuple[bool, Trade]:
        """Place a trade with specified details.

        Parameters
        ----------
        trade : Trade
            The trade to execute.
        Returns
        -------
        tuple of bool and int
            The tuple indicates if the order has been successfully placed,
            whereas the int is the associated order-id.
        """
        raise NotImplementedError

    @abstractmethod
    def cancel_trade(self, trade: Trade):
        """Cancel placed traded.

        Parameters
        ----------
        trade : Trade
            The trade to cancel.
        """
        raise NotImplementedError

    @abstractmethod
    def get_position(self, contract: AContract, *args, **kwargs) -> float:
        """Request the currently held position for a given symbol.

        Parameters
        ----------
        contract : AContract
            The contract definition for which the position is required.
        Returns
        -------
        float
            The current position for the specified symbol.
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
