import json
import threading
from datetime import date, datetime, time
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import logging

import requests
import pandas as pd

try:
    import websocket
except ImportError as e:
    raise ImportError(
        f"Original Error: {e}"
        "\nThe Polygon dependencies are not installed. Please reinstall using"
        " 'pip install algotradepy[polygon]'."
    )

from algotradepy.time_utils import nano_to_seconds, seconds_to_nano


class PolygonRESTConnector:
    _DEFAULT_HOST = "api.polygon.io"
    _EXCHANGES_SUFFIX = "v1/meta/exchanges"
    _TRADES_SUFFIX = "v2/ticks/stocks/trades"

    def __init__(self, api_token: str):
        self._auth_key = api_token
        self._url = "https://" + self._DEFAULT_HOST
        self._session = requests.Session()
        self._session.params["apiKey"] = self._auth_key

    def download_trades_data(
        self, symbol: str, request_date: date, rth: bool = True,
    ) -> pd.DataFrame:
        date_str = request_date.strftime("%Y-%m-%d")
        url = f"{self._url}/{self._TRADES_SUFFIX}/{symbol}/{date_str}"
        params = {
            "limit": 50000,
        }
        if rth:
            start_dt = datetime(
                year=request_date.year,
                month=request_date.month,
                day=request_date.day,
                hour=9,
                minute=30,
            )  # todo: localize
            ts = start_dt.timestamp()
            params["timestamp"] = seconds_to_nano(s=ts)
        resp = self._make_call(endpoint=url, params=params)
        data = self._resp_to_pandas(resp=resp)

        while len(resp["results"]) == 50000:
            ts = nano_to_seconds(resp["results"][-1]["t"])

            if rth and datetime.fromtimestamp(ts).time() >= time(hour=16):
                break

            params["timestamp"] = resp["results"][-1]["t"]
            resp = self._make_call(endpoint=url, params=params)
            next_data = self._resp_to_pandas(resp=resp)
            data = data.append(other=next_data, ignore_index=True)

        if rth:
            end_dt = datetime(
                year=request_date.year,
                month=request_date.month,
                day=request_date.day,
                hour=16,
            )
            ts = end_dt.timestamp()
            end_ts = seconds_to_nano(s=ts)
            data = data[data.loc[:, "t"] <= end_ts]

        return data

    def get_exchanges(self) -> List[Dict]:
        url = f"{self._url}/{self._EXCHANGES_SUFFIX}/"
        resp: List[Dict] = self._make_call(endpoint=url)
        return resp

    def _make_call(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        resp = self._session.get(endpoint, params=params)
        resp = resp.json()
        return resp

    @staticmethod
    def _resp_to_pandas(resp) -> pd.DataFrame:
        results = pd.DataFrame(data=resp["results"])
        return results


class PolygonWSClusters(Enum):
    STOCKS_CLUSTER = "stocks"
    FOREX_CLUSTER = "forex"
    CRYPTO_CLUSTER = "crypto"


class PolygonWebSocketConnector:
    _DEFAULT_HOST = "socket.polygon.io"

    def __init__(
        self,
        api_token: str,
        cluster: PolygonWSClusters = PolygonWSClusters.STOCKS_CLUSTER,
    ):
        self._host = self._DEFAULT_HOST
        self._cluster = cluster
        self._url = f"wss://{self._host}/{cluster.value}"
        self._ws: websocket.WebSocketApp = websocket.WebSocketApp(
            self._url,
            on_open=self._on_open(),
            on_message=self._on_message(),
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._auth_key = api_token
        self._authenticated = threading.Event()
        self._run_thread = None
        self._trade_event_subscribers_lock = threading.Lock()
        self._trade_event_subscribers = []
        self._request_lock = threading.Lock()

    def connect(self):
        self._run_thread = threading.Thread(target=self._ws.run_forever)
        self._run_thread.start()
        self._authenticated.wait()

    def disconnect(self):
        self._ws.close()
        self._run_thread.join()

    def subscribe_to_trade_event(self, func: Callable):
        with self._trade_event_subscribers_lock:
            self._trade_event_subscribers.append(func)

    def unsubscribe_from_trade_event(self, func: Callable):
        with self._trade_event_subscribers_lock:
            self._trade_event_subscribers.remove(func)

    def request_trade_data(self, symbol: str):
        request = {
            "action": "subscribe",
            "params": f"T.{symbol}",
        }
        self._make_request(request=request)

    def cancel_trade_data(self, symbol: str):
        request = {
            "action": "unsubscribe",
            "params": f"T.{symbol}",
        }
        self._make_request(request=request)

    def _on_open(self):
        def f(ws):
            self._authenticate(ws)

        return f

    def _authenticate(self, ws):
        auth_message = json.dumps({"action": "auth", "params": self._auth_key})
        ws.send(auth_message)

    def _on_message(self):
        def f(_, message):
            message = json.loads(message)

            for event in message:
                self._process_event(event=event)

        return f

    def _process_event(self, event: Dict):
        ev = event["ev"]
        if ev == "status":
            self._process_status_event(event=event)
        elif ev == "T":
            self._process_trade_event(event=event)
        else:
            logging.debug(f"Unprocessed polygon web socket event: {event}")

    def _process_status_event(self, event: Dict):
        message = event["message"]
        if message == "authenticated":
            status = event["status"]
            if status == "auth_success":
                self._authenticated.set()
                logging.info("Polygon Web Socket authenticated.")

    def _process_trade_event(self, event: Dict):
        with self._trade_event_subscribers_lock:
            for subscriber in self._trade_event_subscribers:
                subscriber(event)

    def _make_request(self, request: Dict):
        with self._request_lock:
            req_str = json.dumps(request)
            self._ws.send(req_str)

    @staticmethod
    def _on_error(_, error):
        logging.error(msg=error)

    @staticmethod
    def _on_close(_):
        logging.info("Polygon Web Socket closed.")
