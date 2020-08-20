import logging
from datetime import timedelta, datetime
from functools import partial
from typing import Optional, Dict, Callable

from ib_insync import BarDataList
from ib_insync.util import df

from algotradepy.ib_utils import IBBase

try:
    import ib_insync
except ImportError:
    raise ImportError(
        "Optional package ib_insync not install. Please install"
        " using 'pip install ib_insync'."
    )
from ib_insync.ticker import Ticker as _IBTicker

from algotradepy.contracts import AContract, PriceType
from algotradepy.connectors.ib_connector import IBConnector
from algotradepy.streamers.base import ADataStreamer


class IBDataStreamer(ADataStreamer, IBBase):
    """Interactive Brokers Data Streamer class.

    This class implements the ADataStreamer interface for use with the
    Interactive Brokers API. It is an adaptor to the IBConnector, exposing the
    relevant methods.

    Parameters
    ----------
    simulation : bool, default True
        Ignored if parameter `ib_connector` is supplied.
    ib_connector : IBConnector, optional, default None
        A custom instance of the `IBConnector` can be supplied. If not provided,
        it is assumed that the receiver is TWS (see `IBConnector`'s
        documentation for more details).
    """

    def __init__(
        self,
        simulation: bool = True,
        ib_connector: Optional[IBConnector] = None,
    ):
        IBBase.__init__(self, simulation=simulation, ib_connector=ib_connector)

        # {contract: {func: {"price_type": price_type, "kwargs": kwargs}}}
        self._price_subscriptions = {}
        # {contract: {"bars": BarDataList, "funcs": {func: kwargs}}}
        self._bars_subscriptions = {}
        self._market_data_type_set = False

    def subscribe_to_bars(
        self,
        contract: AContract,
        bar_size: timedelta,
        func: Callable,
        fn_kwargs: Optional[dict] = None,
        rth: bool = True,
    ):
        # TODO: test all the different bar sizes
        if fn_kwargs is None:
            fn_kwargs = {}

        self._set_market_data_type()

        def bars_update(
            bars_: BarDataList, has_new_bar: bool, contract_: AContract,
        ):
            assert contract_ in self._bars_subscriptions
            if not has_new_bar:
                return

            bars_df = df(bars_[-1:])
            bars_df = bars_df.set_index("date")
            bar_s = bars_df.iloc[0]

            funcs_dict_ = self._bars_subscriptions[contract_]["funcs"]

            for func_, kwargs_ in funcs_dict_.items():
                func_(bar_s, **kwargs_)

            while len(bars_) != 0:
                bars_.pop()

        previously_requested = contract in self._bars_subscriptions

        con_subs = self._bars_subscriptions.setdefault(contract, {})
        funcs_dict = con_subs.setdefault("funcs", {})
        funcs_dict[func] = fn_kwargs

        if not previously_requested:
            ib_contract = self._to_ib_contract(contract=contract)
            ib_duration = self._get_bars_subscription_duration_str(
                bar_size=bar_size
            )
            ib_bar_size = self._to_ib_bar_size(bar_size=bar_size)
            bars = self._ib_conn.reqHistoricalData(
                contract=ib_contract,
                endDateTime="",
                durationStr=ib_duration,
                barSizeSetting=ib_bar_size,
                whatToShow="MIDPOINT",
                useRTH=rth,
                keepUpToDate=True,
            )
            bars.updateEvent += partial(bars_update, contract_=contract)
            con_subs["bars"] = bars

    def cancel_bars(self, contract: AContract, func: Callable):
        if self._market_data_type_set is None:
            raise RuntimeError("No price subscriptions were requested.")

        found = False
        for sub_contract, sub_dict in self._bars_subscriptions.items():
            if contract == sub_contract and func in sub_dict:
                found = True
                del sub_dict[func]
                if len(sub_dict) == 1:
                    self._cancel_bars_subscription(
                        bars=sub_dict["bars"], contract=contract,
                    )
                    del sub_dict["bars"]
                break

        if not found:
            raise ValueError(
                f"No bars subscription found for contract {contract} and"
                f" function {func}."
            )

    def subscribe_to_tick_data(
        self,
        contract: AContract,
        func: Callable,
        fn_kwargs: Optional[Dict] = None,
        price_type: PriceType = PriceType.MARKET,
    ):
        if fn_kwargs is None:
            fn_kwargs = {}

        self._set_market_data_type()

        def price_update(ticker: _IBTicker):
            contract_ = self._from_ib_contract(ib_contract=ticker.contract)
            assert contract_ in self._price_subscriptions

            con_subs_ = self._price_subscriptions[contract_]

            for func_, func_dict_ in con_subs_.items():
                price_type_ = func_dict_["price_type"]
                fn_kwargs_ = func_dict_["kwargs"]

                if price_type_ == PriceType.MARKET:
                    price_ = ticker.midpoint()
                elif price_type_ == PriceType.ASK:
                    price_ = ticker.ask
                elif price_type_ == PriceType.BID:
                    price_ = ticker.bid
                else:
                    raise TypeError(f"Unknown price type {price_type_}.")

                func_(contract_, price_, **fn_kwargs_)

        previously_requested = contract in self._price_subscriptions

        con_subs = self._price_subscriptions.setdefault(contract, {})
        con_subs[func] = {"price_type": price_type, "kwargs": fn_kwargs}

        if not previously_requested:
            ib_contract = self._to_ib_contract(contract=contract)
            tick = self._ib_conn.reqMktData(
                contract=ib_contract,
                genericTickList="",
                snapshot=False,
                regulatorySnapshot=False,
                mktDataOptions=[],
            )
            tick.updateEvent += price_update

    def cancel_tick_data(self, contract: AContract, func: Callable):
        if self._market_data_type_set is None:
            raise RuntimeError("No price subscriptions were requested.")

        found = False
        for sub_contract, sub_dict in self._price_subscriptions.items():
            if contract == sub_contract and func in sub_dict:
                found = True
                del sub_dict[func]
                if len(sub_dict) == 0:
                    self._cancel_price_subscription(contract=contract)
                break

        if not found:
            raise ValueError(
                f"No price subscription found for contract {contract} and"
                f" function {func}."
            )

    def subscribe_to_trades(
        self,
        contract: AContract,
        func: Callable,
        fn_kwargs: Optional[Dict] = None,
    ):
        raise NotImplementedError

    def cancel_trades(self, contract: AContract, func: Callable):
        raise NotImplementedError

    # ---------------------- Market Data Helpers -------------------------------

    def _set_market_data_type(self):
        if not self._market_data_type_set:
            self._ib_conn.reqMarketDataType(marketDataType=4)
            self._market_data_type_set = True

    def _cancel_price_subscription(self, contract: AContract):
        ib_contract = self._to_ib_contract(contract=contract)
        self._ib_conn.cancelMktData(contract=ib_contract)
        del self._price_subscriptions[contract]

    def _cancel_bars_subscription(
        self, bars: BarDataList, contract: AContract
    ):
        self._ib_conn.cancelHistoricalData(bars=bars)
        del self._bars_subscriptions[contract]

    def _get_bars_subscription_duration_str(self, bar_size: timedelta) -> str:
        self._validate_bar_size(bar_size=bar_size)

        if bar_size == timedelta(seconds=1):
            raise NotImplementedError(
                "Bars of size 1 second not currently supported with IB."
            )
        elif bar_size <= timedelta(minutes=1):
            duration_str = "60 S"
        elif timedelta(minutes=1) < bar_size < timedelta(hours=1):
            duration_str = "3600 S"
        elif timedelta(hours=1) <= bar_size < timedelta(days=1):
            duration_str = "1 D"
        elif timedelta(days=1):
            duration_str = "2 D"
        else:
            raise NotImplementedError(
                "Bars of more than 1 day are not currently supported with IB."
            )

        return duration_str
