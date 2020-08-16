from datetime import timedelta
from typing import Callable, Optional, Dict

import pandas as pd

from algotradepy.contracts import AContract, PriceType
from algotradepy.historical.hist_utils import is_daily
from algotradepy.historical.loaders import HistoricalRetriever
from algotradepy.sim_utils import ASimulationPiece
from algotradepy.streamers.base import ADataStreamer
from algotradepy.time_utils import get_next_trading_date


class SimulationDataStreamer(ADataStreamer, ASimulationPiece):
    """A simulation data streamer.

    This class provides data to the
    :class:`~algotradepy.brokers.sim_broker.SimulationBroker` during a
    simulation.

    Parameters
    ----------
    historical_retriever : HistoricalRetriever
        The historical retriever to use when loading historical data.
    """

    def __init__(
        self, historical_retriever: Optional[HistoricalRetriever] = None,
    ):
        ADataStreamer.__init__(self)
        ASimulationPiece.__init__(self)

        if historical_retriever is None:
            historical_retriever = HistoricalRetriever()
        self._hist_retriever = historical_retriever
        self._local_cache = {}  # {contract: pd.DataFrame}
        # {bar_size: {contract: {func: fn_kwargs}}}
        self._bars_callback_table = {}
        # {contract: {func: {"fn_kwargs": fn_kwargs, "price_type": price_type}}}
        self._tick_callback_table = {}
        self._hist_cache_only = None

    def subscribe_to_bars(
        self,
        contract: AContract,
        bar_size: timedelta,
        func: Callable,
        fn_kwargs: Optional[dict] = None,
        rth: bool = False,
    ):
        # TODO: address rth functionality
        if bar_size < self.sim_clock.time_step:
            raise NotImplementedError(
                f"Attempted to register for a bar-size of {bar_size} in a"
                f" simulation with a time-step of {self.sim_clock.time_step}."
                f" Bar size must be greater or equal to simulation time-step."
            )

        if fn_kwargs is None:
            fn_kwargs = {}

        contract_dict = self._bars_callback_table.setdefault(bar_size, {})
        callbacks = contract_dict.setdefault(contract, {})
        callbacks[func] = fn_kwargs

    def cancel_bars(self, contract: AContract, func: Callable):
        raise NotImplementedError

    def subscribe_to_tick_data(
        self,
        contract: AContract,
        func: Callable,
        fn_kwargs: Optional[Dict] = None,
        price_type: PriceType = PriceType.MARKET,
    ):
        # TODO: test
        if self.sim_clock.time_step != timedelta(seconds=1):
            raise ValueError(
                f"Can only simulate tick data subscription with a clock"
                f" time-step of 1s. Current time-step: {self.sim_clock.time_step}."
            )

        if fn_kwargs is None:
            fn_kwargs = {}

        callbacks = self._tick_callback_table.setdefault(contract, {})
        callbacks[func] = {"fn_kwargs": fn_kwargs, "price_type": price_type}

    def cancel_tick_data(self, contract: AContract, func: Callable):
        if contract in self._tick_callback_table:
            callbacks = self._tick_callback_table[contract]
            if func in callbacks:
                del callbacks[func]
            if len(callbacks) == 0:
                del self._tick_callback_table[contract]

    def subscribe_to_trades(
        self,
        contract: AContract,
        func: Callable,
        fn_kwargs: Optional[Dict] = None,
    ):
        raise NotImplementedError

    def cancel_trades(self, contract: AContract, func: Callable):
        raise NotImplementedError

    # ------------------------- Sim Methods ------------------------------------

    def step(self, cache_only: bool = True):
        self._update_tick_subscribers()
        self._maybe_update_bar_subscribers()

    def get_bar(self, contract: AContract, bar_size: timedelta,) -> pd.Series:
        bar = self._get_next_bar(contract=contract, bar_size=bar_size)
        return bar

    # -------------------------- Helpers ---------------------------------------

    def _update_tick_subscribers(self):
        data = pd.DataFrame()

        for contract, _ in self._tick_callback_table.items():
            symbol_data = self._get_tick_data(contract=contract)
            data = data.append(symbol_data)

        data = data.sort_index(axis=0, level=1)

        for idx, row in data.iterrows():
            contract, dt_ = idx
            callbacks = self._tick_callback_table[contract]

            for func, fn_dict in callbacks.items():
                if fn_dict["price_type"] == PriceType.ASK:
                    price = row["ask"]
                elif fn_dict["price_type"] == PriceType.BID:
                    price = row["bid"]
                else:
                    price = (row["ask"] + row["bid"]) / 2
                func(contract, price, **fn_dict["fn_kwargs"])

    def _get_tick_data(self, contract: AContract) -> pd.DataFrame:
        curr_dt = self.sim_clock.datetime
        prev_dt = curr_dt - timedelta(seconds=1)
        symbol_data = self._get_data(contract=contract, bar_size=timedelta(0),)
        symbol_data = symbol_data.loc[prev_dt:curr_dt]
        ml_index = pd.MultiIndex.from_product([[contract], symbol_data.index])
        symbol_data.index = ml_index
        return symbol_data

    def _maybe_update_bar_subscribers(self):
        step_is_daily = is_daily(bar_size=self.sim_clock.time_step)
        if step_is_daily:
            bar_size = self.sim_clock.time_step
            contract_dict = self._bars_callback_table[bar_size]
            self._update_bar_subscribers(
                bar_size=bar_size, contract_dict=contract_dict,
            )
        else:
            for bar_size, contract_dict in self._bars_callback_table.items():
                sub_is_daily = is_daily(bar_size=bar_size)
                since_epoch = self.sim_clock.datetime.timestamp()
                if (sub_is_daily and self.sim_clock.end_of_day) or (
                    not sub_is_daily and since_epoch % bar_size.seconds == 0
                ):
                    self._update_bar_subscribers(
                        bar_size=bar_size, contract_dict=contract_dict
                    )

    def _update_bar_subscribers(
        self, bar_size: timedelta, contract_dict: dict
    ):
        for contract, callbacks in contract_dict.items():
            bar = self._get_latest_time_entry(
                contract=contract, bar_size=bar_size,
            )
            for func, fn_kwargs in callbacks.items():
                func(bar, **fn_kwargs)

    def _get_latest_time_entry(
        self, contract: AContract, bar_size: timedelta
    ) -> pd.Series:
        bar_data = self._get_data(contract=contract, bar_size=bar_size)
        curr_dt = self.sim_clock.datetime
        if is_daily(bar_size=bar_size):
            bar = bar_data.loc[pd.to_datetime(curr_dt.date())]
        else:
            curr_dt -= bar_size
            bar = bar_data.loc[curr_dt]
        return bar

    def _get_next_bar(
        self, contract: AContract, bar_size: timedelta,
    ) -> pd.Series:
        bar_data = self._get_data(contract=contract, bar_size=bar_size)
        curr_dt = self.sim_clock.datetime
        if is_daily(bar_size=bar_size):
            curr_dt += bar_size
            while curr_dt.date() not in bar_data.index:
                curr_dt += bar_size
            bar = bar_data.loc[curr_dt.date()]
        else:
            bar = bar_data.loc[curr_dt]
        return bar

    def _get_data(
        self, contract: AContract, bar_size: timedelta,
    ) -> pd.DataFrame:
        symbol_data = self._local_cache.get(contract)
        if symbol_data is None:
            symbol_data = {}
            self._local_cache[contract] = symbol_data

        bar_data = symbol_data.get(bar_size)
        if bar_data is None:
            end_date = get_next_trading_date(base_date=self.sim_clock.end_date)
            bar_data = self._hist_retriever.retrieve_bar_data(
                contract=contract,
                bar_size=bar_size,
                start_date=self.sim_clock.start_date,
                end_date=end_date,
                cache_only=self._hist_cache_only,
            )
            symbol_data[bar_size] = bar_data

        return bar_data
