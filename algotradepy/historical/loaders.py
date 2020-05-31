import os
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, List

import pandas as pd
import numpy as np

from algotradepy.historical.hist_utils import (
    bar_size_to_str,
    hist_file_names,
    is_daily,
    DATETIME_FORMAT,
    DATE_FORMAT,
    HIST_DATA_DIR,
)
from algotradepy.historical.providers import AProvider
from algotradepy.time_utils import generate_trading_days


class HistCacheHandler:
    """
    TODO: documentation
    """

    def __init__(self, hist_data_dir: Path = HIST_DATA_DIR):
        self._hist_data_dir = hist_data_dir

    @property
    def base_data_path(self) -> Path:
        return self._hist_data_dir

    @property
    def available_data(self) -> dict:
        raise NotImplementedError

    def get_cached_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        bar_size: timedelta,
    ):
        bar_size_str = bar_size_to_str(bar_size=bar_size)
        path = self.base_data_path / symbol.upper() / bar_size_str
        f_names = hist_file_names(
            start_date=start_date, end_date=end_date, bar_size=bar_size
        )

        data = pd.DataFrame()

        for f_name in f_names:
            f_path = path / f_name
            if os.path.exists(f_path):
                day_data = pd.read_csv(
                    f_path, index_col="datetime", parse_dates=True,
                )
                data = data.append(day_data)

        if len(data) != 0:
            if is_daily(bar_size=bar_size):
                data = data.loc[start_date:end_date]

        return data

    def cache_data(
        self, data: pd.DataFrame, symbol: str, bar_size: timedelta,
    ):
        if len(data) != 0:
            folder_path = (
                self.base_data_path
                / symbol.upper()
                / bar_size_to_str(bar_size=bar_size)
            )
            if not os.path.exists(path=folder_path):
                os.makedirs(name=folder_path)

            if is_daily(bar_size=bar_size):
                file_path = folder_path / "daily.csv"
                if os.path.exists(file_path):
                    day_data = pd.read_csv(
                        file_path, index_col="datetime", parse_dates=True,
                    )
                    data = data.append(day_data).sort_index()
                data.to_csv(file_path, date_format=DATE_FORMAT)
            else:
                data_by_date = data.groupby(pd.Grouper(freq="D"))

                for date_, group in data_by_date:
                    if len(group) != 0:
                        file_name = f"{date_.date().strftime(DATE_FORMAT)}.csv"
                        file_path = folder_path / file_name
                        group.to_csv(file_path, date_format=DATETIME_FORMAT)


class HistoricalRetriever:
    """Retrieves historical data.

    This class downloads and manges historical market data. Multiple APIs
    are available to use for data-downloads.

    Parameters
    ----------
    provider : HistProviders, default HistProvider.IEX
        The historical data provider implementations to use when downloading
        non-cached data.
    hist_data_dir : pathlib.Path, default "../histData"
        The path to the historical data cache.
    """

    def __init__(
        self,
        provider: Optional[AProvider] = None,
        hist_data_dir: Path = HIST_DATA_DIR,
    ):
        self._cache_handler = HistCacheHandler(hist_data_dir=hist_data_dir)
        self._provider = provider

    def retrieve_bar_data(
        self,
        symbol: str,
        bar_size: timedelta,
        start_date: Optional[date],
        end_date: Optional[date],
        cache_only: bool = False,
    ) -> pd.DataFrame:
        """Retrieves the historical data.

        After loading available data from cache, any missing data is downloaded
        from the provider specified during initialization. Downloaded data is
        stored to the cache.

        Parameters
        ----------
        symbol : str
        bar_size : datetime.timedelta
        start_date : datetime.date
        end_date : datetime.date
            If the end date is set to today's date, it will be adjusted to
            yesterday's date to avoid storing partial historical data.
        cache_only : bool
            Prevents data-download on cache-miss.

        Returns
        -------
        data : pd.DataFrame
            The requested historical data.
        """
        if end_date == date.today():
            end_date -= timedelta(days=1)

        data = self._cache_handler.get_cached_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            bar_size=bar_size,
        )

        if not cache_only:
            date_ranges = self._get_missing_date_ranges(
                data=data, start_date=start_date, end_date=end_date,
            )

            for date_range in date_ranges:
                range_data = self._download_data(
                    symbol=symbol,
                    start_date=date_range[0],
                    end_date=date_range[-1],
                    bar_size=bar_size,
                )
                data = data.append(range_data)

                self._cache_handler.cache_data(
                    data=range_data, symbol=symbol, bar_size=bar_size,
                )

        return data

    @staticmethod
    def _get_missing_date_ranges(
        data: pd.DataFrame, start_date: date, end_date: date,
    ) -> List[List[date]]:
        dates = generate_trading_days(start_date=start_date, end_date=end_date)

        if len(data) != 0:
            data_dates = np.unique(data.index.date).tolist()
            date_ranges = []
            date_range = []
            for i in range(len(dates)):
                date_ = dates[i]
                if date_ != data_dates[0]:
                    date_range.append(date_)
                else:
                    data_dates.pop(0)
                    if len(date_range) != 0:
                        date_ranges.append(date_range)
                    if len(data_dates) == 0:
                        if i != len(dates) - 1:
                            date_ranges.append(dates[i + 1 :])
                        break
                    date_range = []
        else:
            date_ranges = [dates]

        return date_ranges

    def _download_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        bar_size: timedelta,
    ):
        data = self._provider.download_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            bar_size=bar_size,
        )
        return data
