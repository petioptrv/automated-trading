from datetime import date, timedelta
from typing import Optional

import pandas as pd

from algotradepy.contracts import AContract
from algotradepy.historical.hist_utils import is_daily
from algotradepy.historical.providers.base import AHistoricalProvider


class YahooHistoricalProvider(AHistoricalProvider):
    """Historical data provider implementation based on the Yahoo! finance API.

    Notes
    -----
    Using `yfinance<https://pypi.org/project/yfinance/>`_ package.
    """

    def __init__(self, simulation: bool = True):
        super().__init__(simulation=simulation)

    def download_bars_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        bar_size: timedelta,
        rth: bool,
        **kwargs,
    ) -> pd.DataFrame:
        # TODO: test rth
        import pandas_datareader as pdr
        import yfinance as yf

        self._validate_bar_size(bar_size=bar_size)

        yf.pdr_override()

        interval = self._get_interval_str(interval=bar_size)
        data = pdr.data.get_data_yahoo(
            contract.symbol,
            interval=interval,
            start=start_date,
            end=end_date + timedelta(days=1),
        )

        if len(data) != 0:
            data = self._format_data(data=data)
            if not is_daily(bar_size=bar_size):
                end_date += timedelta(days=1)
            data = data.loc[start_date:end_date]

        return data

    def download_trades_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        rth: bool,
        **kwargs,
    ):
        raise NotImplementedError("Yahoo does not provide trades data.")

    @staticmethod
    def _validate_bar_size(bar_size: Optional[timedelta]):
        if bar_size == timedelta(0):
            raise ValueError(
                f"{YahooHistoricalProvider.__name__} cannot provide tick data."
            )

    @staticmethod
    def _get_interval_str(interval: timedelta) -> str:
        minute_intervals = [
            timedelta(minutes=1),
            timedelta(minutes=2),
            timedelta(minutes=5),
            timedelta(minutes=15),
            timedelta(minutes=30),
            timedelta(minutes=60),
            timedelta(minutes=90),
        ]
        day_intervals = [
            timedelta(days=1),
        ]

        if interval in minute_intervals:
            interval_str = f"{interval.seconds / 60 :.0f}m"
        elif interval in day_intervals:
            interval_str = f"{interval.days}d"
        else:
            raise ValueError(
                f"Got an unsupported bar size {interval}."
                f" Supported sizes are {minute_intervals + day_intervals}"
            )

        return interval_str

    def _format_data(self, data: pd.DataFrame) -> pd.DataFrame:
        data.index = data.index.tz_localize(None)
        data.index.name = "datetime"

        data.columns = [col.lower() for col in data.columns]
        remaining_cols = [
            col for col in data.columns if col not in self._MAIN_BAR_COLS
        ]
        data = data.loc[:, self._MAIN_BAR_COLS + remaining_cols]

        return data
