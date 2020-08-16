from abc import ABC, abstractmethod
from datetime import date, timedelta

import pandas as pd

from algotradepy.contracts import AContract


class AHistoricalProvider(ABC):
    """An abstract historical data provider.

    Provides methods for downloading data from an API provided by one of the
    implementations.

    Parameters
    ----------
    simulation : bool, default True
        Used in cases where an API provides a simulation mode.
    """

    BARS_SCHEMA_V = 1
    TRADES_SCHEMA_V = 2
    _MAIN_BAR_COLS = ["open", "high", "low", "close", "volume"]
    _MAIN_TRADE_COLS = ["timestamp", "exchange", "size", "price"]

    def __init__(
        self, simulation: bool = True, **kwargs,
    ):
        self.simulation = simulation

    @abstractmethod
    def download_bars_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        bar_size: timedelta,
        rth: bool,
        **kwargs,
    ) -> pd.DataFrame:
        """Download historical data from the provider.

        Parameters
        ----------
        contract : AContract
            The contract definition for which to request historical bar data.
        start_date : datetime.date
            The start date.
        end_date : datetime.date
            The end date.
        bar_size : datetime.timedelta
            The bar size.
        rth : bool, default True
            Restrict to regular trading hours.
        kwargs

        Returns
        -------
        pandas.DataFrame
            The data frame with the values.
        """
        raise NotImplementedError

    @abstractmethod
    def download_trades_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        rth: bool,
        **kwargs,
    ):
        """Download historical data from the provider.

        Parameters
        ----------
        contract : AContract
            The contract definition for which to request historical trades data.
        start_date : datetime.date
            The start date.
        end_date : datetime.date
            The end date.
        rth : bool, default True
            Restrict to regular trading hours.
        kwargs

        Returns
        -------
        pandas.DataFrame
            The data frame with the values.
        """
        raise NotImplementedError
