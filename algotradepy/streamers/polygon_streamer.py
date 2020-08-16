import threading
from datetime import timedelta
from typing import Callable, Optional, Dict

from algotradepy.connectors.polygon_connector import PolygonWebSocketConnector
from algotradepy.contracts import AContract, PriceType, StockContract
from algotradepy.streamers.base import ADataStreamer
from algotradepy.time_utils import milli_to_seconds
from algotradepy.tick import Tick


class PolygonDataStreamer(ADataStreamer):
    def __init__(self, api_token: str):
        self._conn = PolygonWebSocketConnector(api_token=api_token)
        self._conn.connect()
        self._trade_subscribers_lock = threading.Lock()
        self._trade_subscribers = {}  # {contract: {func: fn_kwargs}}

        self._subscribe_to_events()

    def __del__(self):
        self._conn.disconnect()

    def subscribe_to_bars(
        self,
        contract: AContract,
        bar_size: timedelta,
        func: Callable,
        fn_kwargs: Optional[dict] = None,
        rth: bool = False,
    ):
        raise NotImplementedError

    def cancel_bars(self, contract: AContract, func: Callable):
        raise NotImplementedError

    def subscribe_to_tick_data(
        self,
        contract: AContract,
        func: Callable,
        fn_kwargs: Optional[Dict] = None,
        price_type: PriceType = PriceType.MARKET,
    ):
        raise NotImplementedError

    def cancel_tick_data(self, contract: AContract, func: Callable):
        raise NotImplementedError

    def subscribe_to_trades(
        self,
        contract: AContract,
        func: Callable,
        fn_kwargs: Optional[Dict] = None,
    ):
        contract = self._validate_contract(contract=contract)
        if fn_kwargs is None:
            fn_kwargs = {}

        with self._trade_subscribers_lock:
            if contract in self._trade_subscribers:
                self._trade_subscribers[contract][func] = fn_kwargs
            else:
                self._trade_subscribers[contract] = {func: fn_kwargs}
            self._conn.request_trade_data(symbol=contract.symbol)

    def cancel_trades(self, contract: AContract, func: Callable):
        contract = self._validate_contract(contract=contract)

        with self._trade_subscribers_lock:
            if contract not in self._trade_subscribers:
                raise ValueError(
                    f"No subscriptions found for contract {contract}."
                )
            sub_dict = self._trade_subscribers[contract]
            if func not in sub_dict:
                raise ValueError(
                    f"Function {func} not subscribed to contract {contract}."
                )
            del sub_dict[func]
            if len(sub_dict) == 0:
                self._conn.cancel_trade_data(symbol=contract.symbol)

    def _subscribe_to_events(self):
        self._conn.subscribe_to_trade_event(func=self._trades_receiver)

    @staticmethod
    def _validate_contract(contract: AContract) -> AContract:
        if isinstance(contract, StockContract):
            contract = StockContract(symbol=contract.symbol)
        else:
            raise TypeError(f"Unknown contract type {type(contract)}.")

        return contract

    def _trades_receiver(self, trade: Dict):
        contract = StockContract(symbol=trade["sym"])
        tick = self._parse_trade(trade=trade)
        with self._trade_subscribers_lock:
            sub_dict = self._trade_subscribers[contract]
            for func, fn_kwargs in sub_dict.items():
                func(tick, **fn_kwargs)

    @staticmethod
    def _parse_trade(trade: Dict) -> Tick:
        ts = milli_to_seconds(milli=trade["t"])
        tick = Tick(
            timestamp=ts,
            symbol=trade["sym"],
            price=trade["p"],
            size=trade["s"],
        )

        return tick
