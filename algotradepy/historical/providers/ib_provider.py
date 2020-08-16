from datetime import date, timedelta
from typing import Optional

import pandas as pd
from algotradepy.historical.hist_utils import is_daily
from ib_insync import util

from algotradepy.connectors import IBConnector
from algotradepy.ib_utils import IBBase
from algotradepy.time_utils import generate_trading_days

from algotradepy.historical.providers.base import AHistoricalProvider
from algotradepy.contracts import AContract


class IBHistoricalProvider(IBBase, AHistoricalProvider):
    def __init__(
        self,
        simulation: bool = True,
        ib_connector: Optional[IBConnector] = None,
        **kwargs,
    ):
        AHistoricalProvider.__init__(self, simulation=simulation, **kwargs)
        IBBase.__init__(self, simulation=simulation, ib_connector=ib_connector)

    def download_bars_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        bar_size: timedelta,
        rth: bool,
        **kwargs,
    ) -> pd.DataFrame:
        ib_contract = self._to_ib_contract(contract=contract)
        dates = generate_trading_days(start_date=start_date, end_date=end_date)
        duration = f"{len(dates)} D"
        bar_size_str = self._to_ib_bar_size(bar_size=bar_size)

        bar_data = self._ib_conn.reqHistoricalData(
            contract=ib_contract,
            endDateTime=end_date,
            durationStr=duration,
            barSizeSetting=bar_size_str,
            whatToShow="MIDPOINT",
            useRTH=False,
        )
        data = util.df(objs=bar_data)

        if len(data) != 0:
            data = self._format_data(data=data)

        return data

    def download_trades_data(
        self,
        contract: AContract,
        start_date: date,
        end_date: date,
        rth: bool,
        **kwargs,
    ):
        raise NotImplementedError  # TODO: implement

    def _format_data(self, data: pd.DataFrame) -> pd.DataFrame:
        data["date"] = pd.to_datetime(data["date"])
        data = data.set_index("date")
        data.index.name = "datetime"
        data.index = data.index.tz_localize(None)

        remaining_cols = [
            col for col in data.columns if col not in self._MAIN_BAR_COLS
        ]
        data = data.loc[:, self._MAIN_BAR_COLS + remaining_cols]

        return data
