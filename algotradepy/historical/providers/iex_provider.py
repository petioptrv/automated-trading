from datetime import date, timedelta, datetime

import pandas as pd

from algotradepy.connectors.iex_connector import IEXConnector
from algotradepy.contracts import AContract
from algotradepy.historical.hist_utils import is_daily
from algotradepy.historical.providers.base import AHistoricalProvider
from algotradepy.time_utils import generate_trading_days


class IEXHistoricalProvider(AHistoricalProvider):
    """Historical data provider implementation.

    Notes
    -----
    `Data provided by IEX Cloud<https://iexcloud.io>`_
    """

    def __init__(
        self, api_token: str, simulation: bool = True,
    ):
        super().__init__(simulation=simulation)
        self._conn = IEXConnector(api_token=api_token, simulation=simulation)

    def download_bars_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        bar_size: timedelta,
        rth: bool,
        **kwargs,
    ):
        # TODO: test rth
        data = pd.DataFrame()
        dates = generate_trading_days(start_date=start_date, end_date=end_date)
        for date_ in dates:
            day_data = self._conn.download_stock_data(
                symbol=contract.symbol, request_date=date_, bar_size=bar_size,
            )
            data = data.append(other=day_data, ignore_index=True)

        if len(data) != 0:
            if is_daily(bar_size):
                data = self._format_daily_data(data=data)
            else:
                data = self._format_intraday_data(data=data)

        return data

    def download_trades_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        rth: bool,
        **kwargs,
    ):
        # TODO: check if it can be implemented
        raise NotImplementedError

    def _format_daily_data(self, data: pd.DataFrame):
        data["datetime"] = pd.to_datetime(data["date"])
        data = data.drop(["date", "label"], axis=1)
        data = data.set_index(keys="datetime")
        remaining_cols = [
            col for col in data.columns if col not in self._MAIN_BAR_COLS
        ]
        data = data.loc[:, self._MAIN_BAR_COLS + remaining_cols]
        return data

    def _format_intraday_data(self, data: pd.DataFrame):
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
            col for col in data.columns if col not in self._MAIN_BAR_COLS
        ]
        data = data.loc[:, self._MAIN_BAR_COLS + remaining_cols]
        return data
