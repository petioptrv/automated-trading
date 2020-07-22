import json
from datetime import date, timedelta

import requests
import pandas as pd

from algotradepy.historical.hist_utils import is_daily


class IEXConnector:
    _REQ_DATE_FORMAT = "%Y%m%d"

    def __init__(self, api_token: str, simulation: bool):
        self._api_token = api_token
        self._simulation = simulation

    @property
    def _base_url(self) -> str:
        if self._simulation:
            mode = "sandbox"
        else:
            mode = "cloud"

        url = f"https://{mode}.iexapis.com/stable"

        return url

    def download_stock_data(
        self, symbol: str, request_date: date, bar_size: timedelta,
    ) -> pd.DataFrame:
        self._validate_bar_size(bar_size=bar_size)

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

        params["exactDate"] = request_date.strftime(self._REQ_DATE_FORMAT)
        r = requests.get(url=url, params=params)
        json_data = json.loads(r.text)
        data = pd.DataFrame(data=json_data[request_type])

        return data

    @staticmethod
    def _validate_bar_size(bar_size: timedelta):
        if bar_size == timedelta(0):
            raise ValueError(
                f"{IEXConnector.__name__} cannot download tick data."
            )
