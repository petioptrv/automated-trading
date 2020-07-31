from datetime import timedelta
from typing import Optional, Dict, Callable

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

        # {contract: {func: price_type}}
        self._price_subscriptions: Optional[Dict] = None
        self._market_data_type_set = False

    def subscribe_to_bars(
        self,
        contract: AContract,
        bar_size: timedelta,
        func: Callable,
        fn_kwargs: Optional[dict] = None,
    ):
        # TODO: implement
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
        if fn_kwargs is None:
            fn_kwargs = {}

        self._set_market_data_type()

        def price_update(ticker: _IBTicker):
            contract_ = self._from_ib_contract(ib_contract=ticker.contract)
            assert contract_ in self._price_subscriptions

            con_subs_ = self._price_subscriptions[contract_]

            for func_, price_type_ in con_subs_.items():
                if price_type_ == PriceType.MARKET:
                    price_ = ticker.midpoint()
                elif price_type_ == PriceType.ASK:
                    price_ = ticker.ask
                elif price_type_ == PriceType.BID:
                    price_ = ticker.bid
                else:
                    raise TypeError(f"Unknown price type {price_type_}.")

                func_(contract_, price_, **fn_kwargs)

        previously_requested = contract in self._price_subscriptions

        con_subs = self._price_subscriptions.setdefault(contract, {})
        con_subs[func] = price_type

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
            self._price_subscriptions = {}

    def _cancel_all_price_subscriptions(self):
        if self._price_subscriptions is not None:
            sub_contracts = list(self._price_subscriptions.keys())
            for sub_contract in sub_contracts:
                self._cancel_price_subscription(contract=sub_contract)

    def _cancel_price_subscription(self, contract: AContract):
        ib_contract = self._to_ib_contract(contract=contract)
        self._ib_conn.cancelMktData(contract=ib_contract)
        del self._price_subscriptions[contract]
