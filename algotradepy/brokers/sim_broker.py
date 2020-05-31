from datetime import timedelta, date, time, datetime
import time as real_time
from typing import Callable, Optional

import pandas as pd

from algotradepy.brokers.base import ABroker
from algotradepy.historical.hist_utils import is_daily
from algotradepy.historical.loaders import HistoricalRetriever
from algotradepy.time_utils import (
    generate_trading_schedule,
    get_next_trading_date,
)


class SimulationEndException(Exception):
    pass


class SimulationClock:
    def __init__(
        self,
        start_date: date,
        end_date: date,
        simulation_time_step: timedelta = timedelta(minutes=1),
        real_time_per_tick: int = 0,
    ):
        self._start_date = start_date
        self._end_date = end_date
        self._time_step = simulation_time_step
        self._time_per_tick = real_time_per_tick
        self._schedule = generate_trading_schedule(
            start_date=start_date, end_date=end_date,
        )
        self._curr_schedule_index = 0
        self._clock_dt = datetime.combine(
            self._schedule.index[0], self._schedule.iloc[0]["market_open"],
        )

    @property
    def start_date(self) -> date:
        return self._start_date

    @property
    def end_date(self) -> date:
        return self._end_date

    @property
    def time_step(self) -> timedelta:
        return self._time_step

    @property
    def date(self) -> date:
        curr_date = self._clock_dt.date()
        return curr_date

    @property
    def time(self) -> time:
        curr_time = self._clock_dt.time()
        return curr_time

    @property
    def datetime(self) -> datetime:
        return self._clock_dt

    @property
    def start_of_day(self) -> bool:
        idx = self._curr_schedule_index
        open_time = self._schedule.iloc[idx]["market_open"]
        sod = self._clock_dt.time() == open_time
        return sod

    @property
    def end_of_day(self) -> bool:
        idx = self._curr_schedule_index
        close_time = self._schedule.iloc[idx]["market_close"]
        eod = self._clock_dt.time() == close_time
        return eod

    def tick(self):
        real_time.sleep(self._time_per_tick)

        if is_daily(bar_size=self._time_step):
            self._tick_daily()
        else:
            self._tick_intraday()

    def set_datetime(self, dt: datetime):
        if not self._start_date <= dt.date() <= self._end_date:
            raise ValueError(
                f"Date must be between {self._start_date} and"
                f" {self._end_date}. Got {dt.date()}."
            )

        day = self._schedule.loc[dt.date()]

        if not day["market_open"] <= dt.time() < day["market_close"]:
            raise ValueError(
                f"Time must be between {day['market_open']} and"
                f" {day['market_close']}. Got {dt.time()}."
            )

        time_ = dt.time()
        td = timedelta(
            hours=time_.hour, minutes=time_.minute, seconds=time_.second,
        )
        if not td % self._time_step == timedelta():
            raise ValueError(
                f"Cannot set time {time_} for time-step {self._time_step}."
            )

        dates_list = self._schedule.index.to_list()
        idx = dates_list.index(dt.date())

        self._curr_schedule_index = idx
        self._clock_dt = datetime.combine(dt.date(), dt.time())

    def _tick_daily(self):
        idx = self._curr_schedule_index

        if idx == len(self._schedule):
            raise SimulationEndException

        self._clock_dt = datetime.combine(
            self._schedule.index[idx],
            self._schedule.iloc[idx]["market_close"],
        )
        self._curr_schedule_index += 1

    def _tick_intraday(self):
        self._clock_dt += self._time_step

        idx = self._curr_schedule_index
        close_time = self._schedule.iloc[idx]["market_close"]

        if self._clock_dt.time() > close_time:
            day_switch = True
        else:
            day_switch = False

        if day_switch:
            self._curr_schedule_index += 1

            if self._curr_schedule_index == len(self._schedule):
                raise SimulationEndException

            idx = self._curr_schedule_index
            self._clock_dt = datetime.combine(
                self._schedule.index[idx],
                self._schedule.iloc[idx]["market_open"],
            )
            self._clock_dt += self._time_step


class SimulationBroker(ABroker):
    """
    TODO: handle trading-halts.
    """

    def __init__(
        self,
        starting_funds: float,
        transaction_cost: float,
        start_date: date,
        end_date: date,
        simulation_time_step: timedelta = timedelta(minutes=1),
        real_time_per_tick: int = 0,
        starting_positions: Optional[dict] = None,
        hist_retriever: Optional[HistoricalRetriever] = None,
    ):
        ABroker.__init__(self, simulation=True)
        self._clock = SimulationClock(
            start_date=start_date,
            end_date=end_date,
            simulation_time_step=simulation_time_step,
            real_time_per_tick=real_time_per_tick,
        )
        if hist_retriever is None:
            hist_retriever = HistoricalRetriever()
        self._cash = starting_funds
        self._positions = {}
        if starting_positions is not None:
            self._positions.update(**starting_positions)
        self._hist_retriever = hist_retriever
        self._abs_fee = transaction_cost
        self._bars_callback_table = {}
        self._local_cache = {}
        self._hist_cache_only = None

    @property
    def acc_cash(self) -> float:
        return self._cash

    @property
    def datetime(self) -> datetime:
        return self._clock.datetime

    def get_position(self, symbol: str, *args, **kwargs) -> int:
        symbol = symbol.upper()
        position = self._positions.setdefault(symbol, 0)
        return position

    def get_transaction_fee(self) -> float:
        return self._abs_fee

    def run_sim(self, cache_only: bool = True):
        self._hist_cache_only = cache_only

        while True:
            try:
                self._clock.tick()  # advance the time by one candle
                self._maybe_update_subscribers()  # deliver the bar
            except SimulationEndException:
                break

    def subscribe_to_bars(
        self,
        symbol: str,
        bar_size: timedelta,
        func: Callable,
        fn_kwargs: Optional[dict] = None,
    ):
        if bar_size < self._clock.time_step:
            raise NotImplementedError(
                f"Attempted to register for a bar-size of {bar_size} in a"
                f" simulation with a time-step of {self._clock.time_step}."
                f" Bar size must be greater or equal to simulation time-step."
            )

        if fn_kwargs is None:
            fn_kwargs = {}

        callbacks = self._bars_callback_table.setdefault(bar_size, {})
        callbacks[func] = {"symbol": symbol, "kwargs": fn_kwargs}

    def buy(self, symbol: str, n_shares: int) -> bool:
        assert n_shares > 0
        self._add_to_position(symbol=symbol, n_shares=n_shares)
        price = self._get_current_price(symbol=symbol)
        self._cash -= n_shares * price + self.get_transaction_fee()
        return True

    def sell(self, symbol: str, n_shares: int) -> bool:
        assert n_shares > 0
        self._add_to_position(symbol=symbol, n_shares=-n_shares)
        price = self._get_current_price(symbol=symbol)
        self._cash += n_shares * price - self.get_transaction_fee()
        return True

    def _maybe_update_subscribers(self):
        step_is_daily = is_daily(bar_size=self._clock.time_step)
        if step_is_daily:
            bar_size = self._clock.time_step
            callbacks = self._bars_callback_table[bar_size]
            self._update_subscribers(bar_size=bar_size, callbacks=callbacks)
        else:
            for bar_size, callbacks in self._bars_callback_table.items():
                sub_is_daily = is_daily(bar_size=bar_size)
                since_epoch = self._clock.datetime.timestamp()
                if (sub_is_daily and self._clock.end_of_day) or (
                    not sub_is_daily and since_epoch % bar_size.seconds == 0
                ):
                    self._update_subscribers(
                        bar_size=bar_size, callbacks=callbacks
                    )

    def _update_subscribers(self, bar_size: timedelta, callbacks: dict):
        for func, params in callbacks.items():
            symbol = params["symbol"]
            bar = self._get_latest_bar(symbol=symbol, bar_size=bar_size,)
            kwargs = params["kwargs"]
            func(bar, **kwargs)

    def _add_to_position(self, symbol: str, n_shares: int):
        symbol = symbol.upper()
        curr_pos = self._positions.setdefault(symbol, 0)
        self._positions[symbol] = curr_pos + n_shares

    def _get_current_price(self, symbol: str) -> float:
        bar = self._get_next_bar(
            symbol=symbol, bar_size=self._clock.time_step,
        )
        price = bar["open"]
        return price

    def _get_latest_bar(self, symbol: str, bar_size: timedelta) -> pd.Series:
        bar_data = self._get_data(symbol=symbol, bar_size=bar_size,)
        curr_dt = self._clock.datetime
        if is_daily(bar_size=bar_size):
            bar = bar_data.loc[curr_dt.date()]
        else:
            curr_dt -= bar_size
            bar = bar_data.loc[curr_dt]
        return bar

    def _get_next_bar(self, symbol: str, bar_size: timedelta) -> pd.Series:
        bar_data = self._get_data(symbol=symbol, bar_size=bar_size,)
        curr_dt = self._clock.datetime
        if is_daily(bar_size=bar_size):
            curr_dt += bar_size
            while curr_dt.date() not in bar_data.index:
                curr_dt += bar_size
            bar = bar_data.loc[curr_dt.date()]
        else:
            bar = bar_data.loc[curr_dt]
        return bar

    def _get_data(self, symbol: str, bar_size: timedelta) -> pd.DataFrame:
        symbol_data = self._local_cache.get(symbol)
        if symbol_data is None:
            symbol_data = {}
            self._local_cache[symbol] = symbol_data

        bar_data = symbol_data.get(bar_size)
        if bar_data is None:
            end_date = get_next_trading_date(base_date=self._clock.end_date)
            bar_data = self._hist_retriever.retrieve_bar_data(
                symbol=symbol,
                bar_size=bar_size,
                start_date=self._clock.start_date,
                end_date=end_date,
                cache_only=self._hist_cache_only,
            )
            symbol_data[bar_size] = bar_data

        return bar_data
