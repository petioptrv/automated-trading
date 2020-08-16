from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Callable, Optional, Dict

from algotradepy.contracts import AContract, PriceType


class ADataStreamer(ABC):
    @abstractmethod
    def subscribe_to_bars(
        self,
        contract: AContract,
        bar_size: timedelta,
        func: Callable,
        fn_kwargs: Optional[dict] = None,
        rth: bool = False,
    ):
        """Subscribe to receiving historical bar data.

        The bars are fed back as pandas.Series objects.

        Parameters
        ----------
        contract : AContract
            The contract for which to request historical data.
        bar_size : timedelta
            The bar size to request.
        func : Callable
            The function to which to feed the bars.
        fn_kwargs : Dict
            Keyword arguments to feed to the callback function along with the
            bars.
        rth : bool, default False
            Whether to return regular trading hours only.
        """
        raise NotImplementedError

    @abstractmethod
    def cancel_bars(self, contract: AContract, func: Callable):
        """Cancel bar data updates.

        Parameters
        ----------
        contract : AContract
            The contract definition for which to cancel bar updates.
        func : Callable
            The function for which to cancel bar updates.
        """
        raise NotImplementedError

    @abstractmethod
    def subscribe_to_tick_data(
        self,
        contract: AContract,
        func: Callable,
        fn_kwargs: Optional[Dict] = None,
        price_type: PriceType = PriceType.MARKET,
    ):
        """Subscribe to tick updates.

        Parameters
        ----------
        contract : AContract
            The contract definition for which to request price updates.
        func : Callable
            The callback function. It must accept a float as its sole positional
            argument.
        fn_kwargs : dict
            The keyword arguments to pass to the callback function along with
            the positional arguments.
        price_type : PriceType
            The price type (market, bid, ask).
        """
        raise NotImplementedError

    @abstractmethod
    def cancel_tick_data(self, contract: AContract, func: Callable):
        """Cancel tick updates.

        Parameters
        ----------
        contract : AContract
            The contract definition for which to cancel tick updates.
        func : Callable
            The function for which to cancel tick updates.
        """
        raise NotImplementedError

    @abstractmethod
    def subscribe_to_trades(
        self,
        contract: AContract,
        func: Callable,
        fn_kwargs: Optional[Dict] = None,
    ):
        """Subscribe to trade updates.

        Parameters
        ----------
        contract : AContract
            The contract definition for which to request trade updates.
        func : Callable
            The callback function. It must accept a pandas.Series as its sole
            positional argument.
        fn_kwargs : dict
            The keyword arguments to pass to the callback function along with
            the positional arguments.
        """
        raise NotImplementedError

    @abstractmethod
    def cancel_trades(self, contract: AContract, func: Callable):
        """Cancel trade updates.

        Parameters
        ----------
        contract : AContract
            The contract definition for which to cancel trade updates.
        func : Callable
            The function for which to cancel trade updates.
        """
        raise NotImplementedError
