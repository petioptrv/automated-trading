from enum import Enum
from datetime import time, timedelta
import logging
from typing import Optional

import numpy as np
import pandas as pd

from algotradepy.brokers.base import ABroker
from algotradepy.historical.hist_utils import is_daily


class Action(Enum):
    LONG = 0
    SHORT = 1
    CLOSE = 2


class State(Enum):
    ABOVE_UPPER = 0
    ABOVE_SME = 1
    BELOW_SME = 2
    BELOW_LOWER = 3


class SMATrader:
    """
    TODO: extract SMA, EMA in `indicators` package.
    TODO: document
    """

    def __init__(
        self,
        broker: ABroker,
        symbol: str,
        bar_size: timedelta,
        window: int,
        sma_offset: float,
        entry_n_shares: int,
        exit_start: Optional[time] = None,
        full_exit: Optional[time] = None,
        log: bool = False,
    ):
        self._validate(
            symbol=symbol,
            bar_size=bar_size,
            window=window,
            sma_offset=sma_offset,
            entry_n_shares=entry_n_shares,
            exit_start=exit_start,
            full_exit=full_exit,
        )

        self._broker = broker
        self._symbol = symbol
        self._bar_size = bar_size

        self._sma_offset = sma_offset
        self._entry_n_shares = entry_n_shares
        self._daily = is_daily(bar_size=bar_size)
        self._exit_start = exit_start
        self._full_exit = full_exit
        self._log = log

        self._started = False
        self._halted = False
        self._sma_buffer = np.full((window,), np.nan)
        self._sma = None
        self._upper = None
        self._lower = None
        self._bar_count = 0
        self._previous_price_state = None
        self.trades_log = pd.DataFrame(columns=["datetime", "action_code"])

    @property
    def _sme_available(self) -> bool:
        sme_available = not np.any(np.isnan(self._sma_buffer))
        return sme_available

    def start(self):
        if not self._started:
            self._broker.subscribe_to_bars(
                symbol=self._symbol, bar_size=self._bar_size, func=self.step,
            )
        else:
            raise RuntimeError(
                "Attempted to start an already running SMETrader."
            )

    def step(self, bar: pd.Series):
        if self._log:
            logging.info(f"{self} step -> {bar}")

        if not self._daily and bar.name.time() == time(9, 30):
            self._reset()

        if not self._halted and self._sme_available:
            self._maybe_execute_logic(bar=bar)
            self._update_price_state(bar=bar)

        self._update_sma(bar=bar)

    def _update_sma(self, bar: pd.Series):
        bar_index = self._bar_count % len(self._sma_buffer)
        self._sma_buffer[bar_index] = bar["close"]
        self._sma = self._sma_buffer.mean()
        self._upper = self._sma * (1 + self._sma_offset)
        self._lower = self._sma * (1 - self._sma_offset)
        self._bar_count += 1

    def _maybe_execute_logic(self, bar: pd.Series):
        if self._previous_price_state is not None:
            self._maybe_trade(bar=bar)

    def _maybe_trade(self, bar: pd.Series):
        curr_dt = self._broker.datetime
        closing_time = False
        position = self._broker.get_position(symbol=self._symbol)

        if not self._daily and curr_dt.time() >= self._exit_start:
            closing_time = True
            if curr_dt.time() > self._full_exit and position != 0:
                self._close()

        if bar["close"] >= self._upper:
            if position > 0:  # long position
                self._close()
                position = 0
            if position == 0 and not closing_time:
                self._open_short()
        elif bar["close"] < self._lower:
            if position < 0:  # short position
                self._close()
                position = 0
            if position == 0 and not closing_time:
                self._open_long()
        elif bar["close"] >= self._sma:
            if position > 0:
                self._close()  # close long
        else:  # bar["close"] < sme
            if position < 0:
                self._close()  # close short

    def _open_short(self):
        self._broker.sell(symbol=self._symbol, n_shares=self._entry_n_shares)

        if self._log:
            logging.info(f"{self} short -> {self._entry_n_shares}")
            self.trades_log.loc[len(self.trades_log)] = [
                self._broker.datetime,
                Action.SHORT.value,
            ]

    def _open_long(self):
        self._broker.buy(symbol=self._symbol, n_shares=self._entry_n_shares)

        if self._log:
            logging.info(f"{self} short -> {self._entry_n_shares}")
            self.trades_log.loc[len(self.trades_log)] = [
                self._broker.datetime,
                Action.LONG.value,
            ]

    def _close(self):
        position = self._broker.get_position(symbol=self._symbol)

        if position > 0:
            self._broker.sell(symbol=self._symbol, n_shares=position)
        elif position < 0:
            self._broker.buy(symbol=self._symbol, n_shares=abs(position))

        if self._log:
            logging.info(f"{self} closed -> {position}")
            self.trades_log.loc[len(self.trades_log)] = [
                self._broker.datetime,
                Action.CLOSE.value,
            ]

    def _update_price_state(self, bar: pd.Series):
        if bar["close"] >= self._upper:
            self._previous_price_state = State.ABOVE_UPPER
        elif bar["close"] >= self._sma:
            self._previous_price_state = State.ABOVE_SME
        elif bar["close"] >= self._lower:
            self._previous_price_state = State.BELOW_SME
        else:  # bar["close"] < lower
            self._previous_price_state = State.BELOW_LOWER

    def _reset(self):
        self._sma_buffer[:] = np.nan
        self._sma = None
        self._upper = None
        self._lower = None
        self._bar_count = 0
        self._previous_price_state = None

    @staticmethod
    def _validate(
        symbol: str,
        bar_size: timedelta,
        window: int,
        sma_offset: float,
        entry_n_shares: int,
        exit_start: Optional[time] = None,
        full_exit: Optional[time] = None,
    ):
        # TODO: validate symbol
        # TODO: validate bar_size

        if not window > 0 or not isinstance(window, int):
            raise ValueError(
                f"The window parameter must be a positive integer."
                f" Got {window}."
            )
        if not entry_n_shares > 0 or not isinstance(entry_n_shares, int):
            raise ValueError(
                f"The entry_n_shares parameter must be a positive integer."
                f" Got {entry_n_shares}."
            )
        if not is_daily(bar_size=bar_size):
            if exit_start is None or full_exit is None:
                raise ValueError(
                    "When trading intraday, must provide a value for the"
                    " exit_start and full_exit parameters."
                )
