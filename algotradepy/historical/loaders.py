import os
from datetime import date, timedelta, time
from pathlib import Path
from typing import Optional, List

import pandas as pd
import numpy as np

from algotradepy.contracts import (
    AContract,
    StockContract,
    OptionContract,
    ForexContract,
)
from algotradepy.historical.hist_utils import (
    bar_size_to_str,
    hist_file_names,
    is_daily,
    DATETIME_FORMAT,
    DATE_FORMAT,
    HIST_DATA_DIR,
)
from algotradepy.historical.providers.base import AHistoricalProvider
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
        # TODO: implement
        raise NotImplementedError

    def get_cached_bar_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        bar_size: timedelta,
        schema_v: Optional[int] = None,
    ) -> pd.DataFrame:
        data = self._get_cached_data(
            contract=contract,
            start_date=start_date,
            end_date=end_date,
            bar_size=bar_size,
            schema_v=schema_v,
            suffix=bar_size_to_str(bar_size=bar_size),
        )

        return data

    def cache_bar_data(
        self,
        data: pd.DataFrame,
        contract: AContract,
        bar_size: timedelta,
        schema_v: Optional[int] = None,
    ):
        self._cache_data(
            data=data,
            contract=contract,
            bar_size=bar_size,
            schema_v=schema_v,
            suffix=bar_size_to_str(bar_size=bar_size),
        )

    def get_cached_trades_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        schema_v: Optional[int] = None,
    ) -> pd.DataFrame:
        data = self._get_cached_data(
            contract=contract,
            start_date=start_date,
            end_date=end_date,
            bar_size=timedelta(0),
            schema_v=schema_v,
            suffix="trades",
        )

        return data

    def cache_trades_data(
        self,
        data: pd.DataFrame,
        contract: AContract,
        schema_v: Optional[int] = None,
    ):
        self._cache_data(
            data=data,
            contract=contract,
            bar_size=timedelta(0),
            schema_v=schema_v,
            suffix="trades",
        )

    def _cache_data(
        self,
        data: pd.DataFrame,
        contract: AContract,
        bar_size: timedelta,
        schema_v: Optional[int],
        suffix: str,
    ):
        if len(data) != 0:
            contract_type = self._get_con_type(contract=contract)
            symbol = contract.symbol
            folder_path = self.base_data_path / contract_type / symbol / suffix

            if not os.path.exists(path=folder_path):
                os.makedirs(name=folder_path)
                if schema_v:
                    with open(folder_path / ".schema_v", "w") as f:
                        f.write(str(schema_v))

            self._validate_schema(folder_path=folder_path, schema_v=schema_v)
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

    def _get_cached_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        bar_size: timedelta,
        schema_v: Optional[int],
        suffix: str,
    ) -> pd.DataFrame:
        contract_type = self._get_con_type(contract=contract)
        symbol = contract.symbol
        folder_path = self.base_data_path / contract_type / symbol / suffix
        data = pd.DataFrame()

        if not folder_path.exists():
            return data

        self._validate_schema(folder_path=folder_path, schema_v=schema_v)
        file_names = hist_file_names(
            start_date=start_date, end_date=end_date, bar_size=bar_size,
        )

        for file_name in file_names:
            file_path = folder_path / file_name
            if os.path.exists(file_path):
                day_data = pd.read_csv(
                    file_path, index_col="datetime", parse_dates=True,
                )
                data = data.append(day_data)

        if len(data) != 0:
            if is_daily(bar_size=bar_size):
                data = data.loc[start_date:end_date]

        return data

    @staticmethod
    def _get_con_type(contract: AContract) -> str:
        if isinstance(contract, StockContract):
            con_type = "stocks"
        elif isinstance(contract, OptionContract):
            con_type = "options"
        elif isinstance(contract, ForexContract):
            con_type = "forex"
        else:
            raise TypeError(f"Unknown contract type {type(contract)}.")

        return con_type

    @staticmethod
    def _validate_schema(folder_path: Path, schema_v: Optional[int]):
        if schema_v is not None:
            schema_path = folder_path / ".schema_v"
            with open(schema_path, "r") as f:
                folder_schema_v = int(f.read())
            if schema_v != folder_schema_v:
                folder_path_str = os.path.abspath(folder_path)
                raise ValueError(
                    f"Expected folder {folder_path_str} to contain data with"
                    f" schema version {schema_v}, but it contains version"
                    f" {folder_schema_v}."
                )


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

    Notes
    -----
    - TODO: convert to timezone-aware time stamps (GMT)
    - TODO: add exchange info
    """

    def __init__(
        self,
        provider: Optional[AHistoricalProvider] = None,
        hist_data_dir: Path = HIST_DATA_DIR,
    ):
        self._cache_handler = HistCacheHandler(hist_data_dir=hist_data_dir)
        self._provider = provider

    def retrieve_bar_data(
        self,
        contract: AContract,
        bar_size: timedelta,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        cache_only: bool = False,
        cache_downloads: bool = True,
        rth: bool = True,
        allow_partial: bool = False,
    ) -> pd.DataFrame:
        """Retrieves the historical data.

        After loading available data from cache, any missing data is downloaded
        from the provider specified during initialization. Downloaded data is
        stored to the cache.

        Parameters
        ----------
        contract : AContract
        bar_size : datetime.timedelta
        start_date : datetime.date, optional, default None
        end_date : datetime.date, optional, default None
            If the end date is set to today's date, it will be adjusted to
            yesterday's date to avoid storing partial historical data.
        cache_only : bool, default False
            Prevents data-download on cache-miss.
        cache_downloads : bool, default True
            Whether to cache downloaded data.
        rth : bool, default True
            Restrict to regular trading hours.
        allow_partial : bool, default False
            Allows downloading of partial data for today's date. This partial
            data is never cached.

        Returns
        -------
        data : pd.DataFrame
            The requested historical data.
        """
        if end_date == date.today():
            if not allow_partial:
                end_date -= timedelta(days=1)
                end_cache_date = end_date
            else:
                end_cache_date = end_date - timedelta(days=1)
        else:
            end_cache_date = end_date

        if end_cache_date >= start_date:
            data = self._cache_handler.get_cached_bar_data(
                contract=contract,
                start_date=start_date,
                end_date=end_date,
                bar_size=bar_size,
                schema_v=AHistoricalProvider.BARS_SCHEMA_V,
            )
        else:
            data = pd.DataFrame()

        if not cache_only:
            date_ranges = self._get_missing_date_ranges(
                data=data, start_date=start_date, end_date=end_date,
            )

            for date_range in date_ranges:
                range_data = self._provider.download_bars_data(
                    contract=contract,
                    start_date=date_range[0],
                    end_date=date_range[-1],
                    bar_size=bar_size,
                    rth=False,
                )
                data = data.append(range_data)

                if cache_downloads:
                    range_data = range_data[
                        range_data.index <= pd.to_datetime(end_cache_date)
                    ]
                    self._cache_handler.cache_bar_data(
                        data=range_data,
                        contract=contract,
                        bar_size=bar_size,
                        schema_v=AHistoricalProvider.BARS_SCHEMA_V,
                    )

        if rth and not is_daily(bar_size=bar_size):
            data = data.between_time(
                start_time=time(9, 30), end_time=time(16), include_end=False,
            )

        return data

    def retrieve_trades_data(
        self,
        contract: AContract,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        cache_only: bool = False,
        cache_downloads: bool = True,
        rth: bool = True,
        allow_partial: bool = False,
    ) -> pd.DataFrame:
        """Retrieves the historical data.

        After loading available data from cache, any missing data is downloaded
        from the provider specified during initialization. Downloaded data is
        stored to the cache.

        Parameters
        ----------
        contract : AContract
        start_date : datetime.date, optional, default None
        end_date : datetime.date, optional, default None
            If the end date is set to today's date and `allow_partial` is set
            to `False`, the end-date will be adjusted to yesterday's date.
        cache_only : bool, default False
            Prevents data-download on cache-miss.
        cache_downloads : bool, default True
            Whether to cache downloaded data.
        rth : bool, default True
            Restrict to regular trading hours.
        allow_partial : bool, default False
            Allows downloading of partial data for today's date. This partial
            data is never cached.

        Returns
        -------
        data : pd.DataFrame
            The requested historical data.
        """
        if end_date == date.today():
            if not allow_partial:
                end_date -= timedelta(days=1)
                end_cache_date = end_date
            else:
                end_cache_date = end_date - timedelta(days=1)
        else:
            end_cache_date = end_date

        if end_cache_date >= start_date:
            data = self._cache_handler.get_cached_trades_data(
                contract=contract,
                start_date=start_date,
                end_date=end_cache_date,
                schema_v=AHistoricalProvider.TRADES_SCHEMA_V,
            )
        else:
            data = pd.DataFrame()

        if not cache_only:
            date_ranges = self._get_missing_date_ranges(
                data=data, start_date=start_date, end_date=end_date,
            )

            for date_range in date_ranges:
                range_data = self._provider.download_trades_data(
                    contract=contract,
                    start_date=date_range[0],
                    end_date=date_range[-1],
                    rth=rth,
                )
                data = data.append(range_data)

                if cache_downloads:
                    range_data = range_data[
                        range_data.index <= pd.to_datetime(end_cache_date)
                    ]
                    self._cache_handler.cache_trades_data(
                        data=range_data,
                        contract=contract,
                        schema_v=AHistoricalProvider.TRADES_SCHEMA_V,
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
