import json
from abc import ABC, abstractmethod
from datetime import date, timedelta, datetime
from typing import Optional

import pandas as pd
import requests

from algotradepy.historical.hist_utils import is_daily
from algotradepy.time_utils import generate_trading_days


class AProvider(ABC):
    """An abstract historical data provider.

    Provides methods for downloading data from an API provided by one of the
    implementations.

    Parameters
    ----------
    api_token : str, optional, default None
    simulation : bool, default True
        Used in cases where an API provides a simulation mode.
    """

    _MAIN_COLS = ["open", "high", "low", "close", "volume"]

    def __init__(
        self, api_token: Optional[str] = None, simulation: bool = True,
    ):
        self._api_token = api_token
        self.simulation = simulation

    @abstractmethod
    def download_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        bar_size: timedelta,
        **kwargs,
    ) -> pd.DataFrame:
        """Download historical data from the provider.

        Parameters
        ----------
        symbol : str
        start_date : datetime.date
        end_date : datetime.date
        bar_size : datetime.timedelta
        kwargs

        Returns
        -------

        """
        raise NotImplementedError


class YahooProvider(AProvider):
    """Historical data provider implementation based on the Yahoo! finance API.

    Notes
    -----
    Using `yfinance<https://pypi.org/project/yfinance/>`_ package.
    """

    def __init__(
        self, api_token: Optional[str] = None, simulation: bool = True
    ):
        super().__init__(api_token=api_token, simulation=simulation)

    def download_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        bar_size: timedelta,
        **kwargs,
    ) -> pd.DataFrame:
        import pandas_datareader as pdr
        import yfinance as yf

        yf.pdr_override()

        interval = self._get_interval_str(interval=bar_size)
        data = pdr.data.get_data_yahoo(
            symbol,
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
            col for col in data.columns if col not in self._MAIN_COLS
        ]
        data = data.loc[:, self._MAIN_COLS + remaining_cols]

        return data


class IEXProvider(AProvider):
    """Historical data provider implementation.

    TODO: Extract server-comm functionality into a connector.

    Notes
    -----
    `Data provided by IEX Cloud<https://iexcloud.io>`_
    """

    _REQ_DATE_FORMAT = "%Y%m%d"

    def __init__(
        self, api_token: Optional[str] = None, simulation: bool = True
    ):
        super().__init__(api_token=api_token, simulation=simulation)

    @property
    def _base_url(self) -> str:
        if self.simulation:
            mode = "sandbox"
        else:
            mode = "cloud"

        url = f"https://{mode}.iexapis.com/stable"

        return url

    def download_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        bar_size: timedelta,
        **kwargs,
    ):
        params = {"token": self._api_token}

        if is_daily(bar_size=bar_size):
            request_type = "chart"
            params["chartByDay"] = True
            params["range"] = "date"
        elif bar_size == timedelta(minutes=1):
            request_type = "intraday-prices"
            params["range"] = "1d"
        else:
            raise ValueError(
                f"{type(self)} can only download historical data or"
                f" 1-minute bars. Got a bar size of {bar_size}."
            )

        params["types"] = [request_type]
        url = f"{self._base_url}/stock/{symbol.lower()}/batch"

        data = pd.DataFrame()
        dates = generate_trading_days(start_date=start_date, end_date=end_date)
        for date_ in dates:
            params["exactDate"] = date_.strftime(self._REQ_DATE_FORMAT)
            r = requests.get(url=url, params=params)
            json_data = json.loads(r.text)
            day_data = pd.DataFrame(data=json_data[request_type])
            data = data.append(other=day_data, ignore_index=True)

        if len(data) != 0:
            if is_daily(bar_size):
                data = self._format_daily_data(data=data)
            else:
                data = self._format_intraday_data(data=data)

        return data

    def _format_daily_data(self, data: pd.DataFrame):
        data["datetime"] = pd.to_datetime(data["date"])
        data = data.drop(["date", "label"], axis=1)
        data = data.set_index(keys="datetime")
        remaining_cols = [
            col for col in data.columns if col not in self._MAIN_COLS
        ]
        data = data.loc[:, self._MAIN_COLS + remaining_cols]
        return data

    def _format_intraday_data(self, data: pd.DataFrame):
        # ugly things happen here... ugly, but optimized
        data["datetime"] = data.apply(
            func=lambda x: datetime.combine(
                datetime.strptime(x["date"], "%Y-%m-%d").date(),
                datetime.strptime(x["minute"], "%H:%M").time(),
            ),
            axis=1,
        )
        data = data.drop(["date", "minute", "label"], axis=1)
        data = data.set_index(keys="datetime")
        remaining_cols = [
            col for col in data.columns if col not in self._MAIN_COLS
        ]
        data = data.loc[:, self._MAIN_COLS + remaining_cols]
        return data
