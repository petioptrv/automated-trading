from enum import Enum
from datetime import time, timedelta
import logging

import numpy as np
import pandas as pd

from algotradepy.brokers import ABroker


class Action(Enum):
    LONG = 0
    SHORT = 1
    CLOSE = 2


class State(Enum):
    ABOVE_UPPER = 0
    ABOVE_SME = 1
    BELOW_SME = 2
    BELOW_LOWER = 3


class SMETrader:
    def __init__(
            self,
            broker: ABroker,
            symbol: str,
            bar_size: timedelta,
            window: int,
            sme_offset: float,
            entry_n_shares: int,
            # exit_start: time,
            # full_exit: time,
    ):
        self._broker = broker
        self._symbol = symbol
        self._bar_size = bar_size

        self._sme_offset = sme_offset
        self._entry_n_shares = entry_n_shares
        # self._exit_start = exit_start
        # self._full_exit = full_exit

        self._started = False
        self._halted = False
        self._sme_buffer = np.full((window,), np.nan)
        self._sme = None
        self._upper = None
        self._lower = None
        self._bar_count = 0
        self._previous_price_state = None

    def start(self):
        if not self._started:
            self._broker.register_for_bars(
                symbol=self._symbol,
                bar_size=self._bar_size,
                func=self.step,
            )
        else:
            raise RuntimeError(
                "Attempted to start an already running SMETrader."
            )

    def step(self, bar: pd.Series):
        logging.log(0, f"{self} step -> {bar}")

        if bar.name.time() == time(9, 30):
            self._reset()

        self._update_sme(bar=bar)

        sme_available = not np.any(np.isnan(self._sme_buffer))

        if not self._halted and sme_available:
            self._execute_logic(bar=bar)

    def _update_sme(self, bar: pd.Series):
        bar_index = self._bar_count % len(self._sme_buffer)
        self._sme_buffer[bar_index] = bar["close"]
        self._sme = self._sme_buffer.mean()
        self._upper = self._sme * (1 + self._sme_offset)
        self._lower = self._sme * (1 - self._sme_offset)
        self._bar_count += 1

    def _execute_logic(self, bar: pd.Series):
        if self._previous_price_state is not None:
            self._maybe_trade(bar=bar)

        self._update_price_state(bar=bar)

    def _maybe_trade(self, bar: pd.Series):
        if bar["close"] >= self._upper:
            if self._previous_price_state != State.ABOVE_UPPER:
                self._open_short()
        elif bar["close"] < self._lower:
            if self._previous_price_state != State.BELOW_LOWER:
                self._open_long()
        elif bar["close"] >= self._sme:
            if self._previous_price_state == State.BELOW_LOWER:
                self._close()  # close long
        else:  # bar["close"] < sme
            if self._previous_price_state == State.ABOVE_UPPER:
                self._close()  # close short

    def _open_short(self):
        position = self._broker.get_position(symbol=self._symbol)

        assert position >= 0  # otherwise, something's wrong

        n_shares = position + self._entry_n_shares
        self._broker.sell(symbol=self._symbol, n_shares=n_shares)
        logging.log(0, f"{self} short -> {n_shares}")

    def _open_long(self):
        position = self._broker.get_position(symbol=self._symbol)

        assert position <= 0  # otherwise, something's wrong

        n_shares = abs(position) + self._entry_n_shares
        self._broker.buy(symbol=self._symbol, n_shares=n_shares)
        logging.log(0, f"{self} short -> {n_shares}")

    def _close(self):
        position = self._broker.get_position(symbol=self._symbol)

        if position > 0:
            self._broker.sell(symbol=self._symbol, n_shares=position)
        elif position < 0:
            self._broker.buy(symbol=self._symbol, n_shares=position)

        logging.log(0, f"{self} closed -> {position}")

    def _update_price_state(self, bar: pd.Series):
        if bar["close"] >= self._upper:
            self._previous_price_state = State.ABOVE_UPPER
        elif bar["close"] >= self._sme:
            self._previous_price_state = State.ABOVE_SME
        elif bar["close"] >= self._lower:
            self._previous_price_state = State.BELOW_SME
        else:  # bar["close"] < lower
            self._previous_price_state = State.BELOW_LOWER

    def _reset(self):
        self._sme = None
        self._upper = None
        self._lower = None
        self._bar_count = 0
        self._previous_price_state = None
