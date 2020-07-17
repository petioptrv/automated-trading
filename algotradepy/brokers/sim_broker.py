from datetime import timedelta, date, time, datetime
import time as real_time
from typing import Callable, Optional, Dict, Tuple, List

import pandas as pd

from algotradepy.brokers.base import ABroker
from algotradepy.contracts import AContract, PriceType
from algotradepy.historical.hist_utils import is_daily
from algotradepy.historical.loaders import HistoricalRetriever
from algotradepy.orders import (
    AnOrder,
    LimitOrder,
    OrderAction,
    MarketOrder,
)
from algotradepy.trade import TradeState, TradeStatus, Trade
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
        self._cash = starting_funds
        self._positions = {}
        if starting_positions is not None:
            self._positions.update(**starting_positions)
        if hist_retriever is None:
            hist_retriever = HistoricalRetriever()
        self._hist_retriever = hist_retriever
        self._abs_fee = transaction_cost
        # {bar_size: {contract: {func: fn_kwargs}}}
        self._bars_callback_table = {}
        # {contract: {func: {"fn_kwargs": fn_kwargs, "price_type": price_type}}}
        self._tick_callback_table = {}
        # {contract: pd.DataFrame}
        self._local_cache = {}
        self._hist_cache_only = None
        self._valid_id = 1
        self._new_trade_subscribers = []
        self._trade_updates_subscribers = []
        self._placed_trades: List[Trade] = []

    @property
    def acc_cash(self) -> float:
        return self._cash

    @property
    def datetime(self) -> datetime:
        return self._clock.datetime

    @property
    def trades(self) -> List[Trade]:
        return self._placed_trades

    @property
    def open_trades(self) -> List[Trade]:
        done_statuses = [TradeState.CANCELLED, TradeState.FILLED]
        open_trades = []
        for trade in self._placed_trades:
            if trade.status.state not in done_statuses:
                open_trades.append(trade)

        return open_trades

    def sleep(self, secs: float):
        real_time.sleep(secs=secs)

    def subscribe_to_new_trades(
            self, func: Callable, fn_kwargs: Optional[Dict] = None,
    ):
        # TODO: test
        if fn_kwargs is None:
            fn_kwargs = {}
        self._new_trade_subscribers.append((func, fn_kwargs))

    def subscribe_to_trade_updates(
            self, func: Callable, fn_kwargs: Optional[Dict] = None,
    ):
        # TODO: test
        if fn_kwargs is None:
            fn_kwargs = {}
        self._trade_updates_subscribers.append((func, fn_kwargs))

    def subscribe_to_bars(
        self,
        contract: AContract,
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

        contract_dict = self._bars_callback_table.setdefault(bar_size, {})
        callbacks = contract_dict.setdefault(contract, {})
        callbacks[func] = fn_kwargs

    def subscribe_to_tick_data(
        self,
        contract: AContract,
        func: Callable,
        fn_kwargs: Optional[Dict] = None,
        price_type: PriceType = PriceType.MARKET,
    ):
        # TODO: test
        if self._clock.time_step != timedelta(seconds=1):
            raise ValueError(
                f"Can only simulate tick data subscription with a clock"
                f" time-step of 1s. Current time-step: {self._clock.time_step}."
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

    def place_trade(self, trade: Trade, *args, **kwargs) -> Tuple[bool, Trade]:
        trade_id = self._get_increment_valid_id()
        order = trade.order
        order._order_id = trade_id
        new_status = TradeStatus(
            state=TradeState.SUBMITTED,
            filled=0,
            remaining=order.quantity,
            ave_fill_price=0,
            order_id=trade_id,
        )
        new_trade = Trade(
            contract=trade.contract,
            order=order,
            status=new_status,
        )
        self._placed_trades.append(new_trade)

        self._update_trade_updates_subscribers(trade=new_trade)

        if isinstance(trade.order, MarketOrder):
            # TODO: This should be smarter... What if liquidity is low?
            # maybe should remove it and only use self.simulate_trade_execution
            self._execute_trade(trade=trade)

        # update trade placed subscribers
        for func, fn_kwargs in self._new_trade_subscribers:
            func(trade, **fn_kwargs)

        return True, trade

    def cancel_trade(self, trade: Trade):
        # TODO: implement
        cancelled_status = TradeStatus(
            state=TradeState.CANCELLED,
            filled=trade.status.filled,
            remaining=trade.status.remaining,
            ave_fill_price=trade.status.ave_fill_price,
            order_id=trade.status.order_id,
        )
        new_trade = Trade(
            contract=trade.contract,
            order=trade.order,
            status=cancelled_status,
        )
        trade_idx = self._placed_trades.index(trade)
        self._placed_trades[trade_idx] = new_trade

        self._update_trade_updates_subscribers(trade=trade)

    def get_position(self, contract: AContract, *args, **kwargs) -> float:
        symbol = contract.symbol
        position = self._positions.setdefault(symbol, 0)
        return position

    def get_transaction_fee(self) -> float:
        return self._abs_fee

    def run_sim(
        self, step_count: Optional[int] = None, cache_only: bool = True,
    ):
        # TODO: test step_count
        self._hist_cache_only = cache_only
        i = 0

        while True:
            try:
                self._clock.tick()
                self._update_tick_subscribers()
                self._maybe_update_bar_subscribers()
            except SimulationEndException:
                break

            i += 1
            if i == step_count:
                break

    def simulate_trade_execution(
        self,
        trade: Trade,
        price: Optional[float] = None,
        n_shares: Optional[float] = None,
    ):
        # TODO: test
        # TODO: implement for Limit and Stop Loss Orders
        self._execute_trade(
            trade=trade, price=price, n_shares=n_shares,
        )

    def _get_increment_valid_id(self) -> int:
        valid_id = self._valid_id
        self._valid_id += 1
        return valid_id

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
        curr_dt = self._clock.datetime
        next_dt = curr_dt + timedelta(seconds=1)
        symbol_data = self._get_data(
            contract=contract, bar_size=timedelta(0),
        )
        symbol_data = symbol_data.loc[curr_dt:next_dt]
        ml_index = pd.MultiIndex.from_product([[contract], symbol_data.index])
        symbol_data.index = ml_index
        return symbol_data

    def _maybe_update_bar_subscribers(self):
        step_is_daily = is_daily(bar_size=self._clock.time_step)
        if step_is_daily:
            bar_size = self._clock.time_step
            contract_dict = self._bars_callback_table[bar_size]
            self._update_bar_subscribers(
                bar_size=bar_size, contract_dict=contract_dict,
            )
        else:
            for bar_size, contract_dict in self._bars_callback_table.items():
                sub_is_daily = is_daily(bar_size=bar_size)
                since_epoch = self._clock.datetime.timestamp()
                if (sub_is_daily and self._clock.end_of_day) or (
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

    def _execute_trade(
        self,
        trade: Trade,
        price: Optional[float] = None,
        n_shares: Optional[float] = None,
    ):
        trade_idx = self._placed_trades.index(trade)
        trade = self._placed_trades[trade_idx]
        contract = trade.contract
        order = trade.order
        filled = trade.status.filled

        if n_shares is not None:
            assert n_shares <= order.quantity - filled
        else:
            n_shares = order.quantity - filled

        if price is None:
            price = self._get_current_price(contract=contract)

        if isinstance(order, LimitOrder):
            if order.action == OrderAction.BUY:
                assert price <= order.limit_price
            else:
                assert price >= order.limit_price

        if order.action == OrderAction.BUY:
            self._cash -= n_shares * price + self.get_transaction_fee()
            self._add_to_position(symbol=contract.symbol, n_shares=n_shares)
        else:
            self._cash += n_shares * price + self.get_transaction_fee()
            self._add_to_position(symbol=contract.symbol, n_shares=-n_shares)

        filled = trade.status.filled
        new_filled = filled + n_shares
        ave_price = trade.status.ave_fill_price
        new_ave_price = (ave_price * filled + price * n_shares) / new_filled
        new_status = TradeStatus(
            state=TradeState.FILLED,
            filled=new_filled,
            remaining=order.quantity - filled,
            ave_fill_price=new_ave_price,
            order_id=order.order_id,
        )
        new_trade = Trade(
            contract=contract,
            order=order,
            status=new_status,
        )
        self._placed_trades[trade_idx] = new_trade
        self._update_trade_updates_subscribers(trade=trade)

    def _add_to_position(self, symbol: str, n_shares: float):
        symbol = symbol.upper()
        curr_pos = self._positions.setdefault(symbol, 0)
        self._positions[symbol] = curr_pos + n_shares

    def _update_trade_updates_subscribers(self, trade: Trade):
        trade_idx = self._placed_trades.index(trade)
        trade = self._placed_trades[trade_idx]
        status = trade.status

        for func, fn_kwargs in self._trade_updates_subscribers:
            func(status, **fn_kwargs)

    def _get_current_price(self, contract: AContract) -> float:
        # TODO: use 1s aggregation of ticks, if available
        bar = self._get_next_bar(
            contract=contract, bar_size=self._clock.time_step,
        )
        price = bar["open"]
        return price

    def _get_latest_time_entry(
        self, contract: AContract, bar_size: timedelta
    ) -> pd.Series:
        bar_data = self._get_data(contract=contract, bar_size=bar_size)
        curr_dt = self._clock.datetime
        if is_daily(bar_size=bar_size):
            bar = bar_data.loc[curr_dt.date()]
        else:
            curr_dt -= bar_size
            bar = bar_data.loc[curr_dt]
        return bar

    def _get_next_bar(
            self, contract: AContract, bar_size: timedelta,
    ) -> pd.Series:
        bar_data = self._get_data(contract=contract, bar_size=bar_size)
        curr_dt = self._clock.datetime
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
            end_date = get_next_trading_date(base_date=self._clock.end_date)
            bar_data = self._hist_retriever.retrieve_bar_data(
                symbol=contract.symbol,
                bar_size=bar_size,
                start_date=self._clock.start_date,
                end_date=end_date,
                cache_only=self._hist_cache_only,
            )
            symbol_data[bar_size] = bar_data

        return bar_data
