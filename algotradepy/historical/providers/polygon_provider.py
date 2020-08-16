from datetime import date, timedelta, datetime
from typing import Dict
from functools import partial

import numpy as np
import pandas as pd

from algotradepy.connectors.polygon_connector import PolygonRESTConnector
from algotradepy.contracts import AContract, Exchange
from algotradepy.historical.providers.base import AHistoricalProvider
from algotradepy.time_utils import (
    generate_trading_days,
    nano_to_seconds,
)


class PolygonHistoricalProvider(AHistoricalProvider):
    def __init__(
        self, api_token: str, simulation: bool = True,
    ):
        super().__init__(simulation=simulation)
        self._conn = PolygonRESTConnector(api_token=api_token)
        self._exchange_mapping = self._build_exchange_map()

    def download_bars_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        bar_size: timedelta,
        rth: bool,
        **kwargs,
    ) -> pd.DataFrame:
        # TODO: implement
        raise NotImplementedError

    def download_trades_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        rth: bool,
        **kwargs,
    ) -> pd.DataFrame:
        data = pd.DataFrame()
        dates = generate_trading_days(start_date=start_date, end_date=end_date)

        for date_ in dates:
            day_data = self._conn.download_trades_data(
                symbol=contract.symbol, request_date=date_, rth=rth
            )
            data = data.append(other=day_data, ignore_index=True)

        data = self._format_trades_data(data=data)

        return data

    def _format_trades_data(self, data: pd.DataFrame) -> pd.DataFrame:
        data["timestamp"] = data["t"] / 1e9
        data.index = pd.to_datetime(data["t"], unit="ns")
        data.index.name = "datetime"
        data = data.rename({"s": "size", "p": "price"}, axis=1)
        data["exchange"] = data["x"].apply(
            partial(self._exchange_mapping.get, np.nan),
        )
        data = data.loc[:, ["timestamp", "exchange", "size", "price"]]

        return data

    def _build_exchange_map(self) -> Dict[int, Exchange]:
        poly_exchanges = self._conn.get_exchanges()
        exchanges = list(map(lambda e: e.value, Exchange))
        exchange_map = {}

        for ex in poly_exchanges:
            ex_name = ex["name"].split(" ")[0]
            if ex_name in exchanges:
                exchange_map[ex["id"]] = ex_name

        return exchange_map
