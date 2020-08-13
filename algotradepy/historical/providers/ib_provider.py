from datetime import date, timedelta
from typing import Optional

import pandas as pd
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
        ib_data_df = util.df(objs=bar_data)

        # TODO: test!!!!
        data = pd.DataFrame(
            data={
                "open": ib_data_df["Open"],
                "high": ib_data_df["High"],
                "low": ib_data_df["Low"],
                "close": ib_data_df["Close"],
                "volume": ib_data_df["Volume"],
            }
        )

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
