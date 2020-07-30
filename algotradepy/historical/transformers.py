from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from algotradepy.contracts import AContract
from algotradepy.historical.loaders import HistCacheHandler
from algotradepy.historical.hist_utils import HIST_DATA_DIR


class HistoricalAggregator:
    def __init__(self, hist_data_dir: Path = HIST_DATA_DIR):
        self._cache_handler = HistCacheHandler(hist_data_dir=hist_data_dir)

    def aggregate_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        base_bar_size: timedelta,
        target_bar_size: timedelta,
    ):
        if target_bar_size < base_bar_size:
            raise ValueError(
                f"Cannot aggregate from {base_bar_size} bars to"
                f" {target_bar_size} bars. Target must be larger than base."
            )

        data = self._cache_handler.get_cached_bar_data(
            contract=contract,
            start_date=start_date,
            end_date=end_date,
            bar_size=base_bar_size,
        )

        bars_freq = self._get_bars_freq(bar_size=target_bar_size)
        bar_groups = data.groupby(
            [pd.Grouper(freq="D"), pd.Grouper(freq=bars_freq)]
        )
        data = bar_groups.agg(
            open=pd.NamedAgg(column="open", aggfunc="first"),
            high=pd.NamedAgg(column="high", aggfunc="max"),
            low=pd.NamedAgg(column="low", aggfunc="min"),
            close=pd.NamedAgg(column="close", aggfunc="last"),
            volume=pd.NamedAgg(column="volume", aggfunc="sum"),
        )
        data.index = data.index.droplevel(0)

        self._cache_handler.cache_bar_data(
            data=data, contract=contract, bar_size=target_bar_size,
        )

        return data

    @staticmethod
    def _get_bars_freq(bar_size: timedelta) -> str:
        if bar_size < timedelta(minutes=1):
            freq = f"{int(bar_size.seconds)}S"
        elif bar_size < timedelta(hours=1):
            freq = f"{int(bar_size.seconds / 60)}min"
        elif bar_size == timedelta(days=1):
            freq = "D"
        else:
            raise ValueError(f"No frequency available for {bar_size}.")

        return freq
