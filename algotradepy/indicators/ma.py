from abc import ABC, abstractmethod

import numpy as np


class AMA(ABC):
    @property
    def ready(self) -> bool:
        return not np.isnan(self.value)

    @property
    @abstractmethod
    def value(self) -> np.float64:
        raise NotImplementedError


class SMA(AMA):
    def __init__(self, n_periods: int):
        self._values = np.array([np.nan] * n_periods)
        self._bar_count = 0

    @property
    def value(self) -> np.float64:
        val = self._values.mean()
        return val

    def update(self, value: float):
        idx = self._bar_count % len(self._values)
        self._values[idx] = value
        self._bar_count += 1


class EMA:
    def __init__(self, n_periods: int):
        self._n_periods = n_periods
        self._factor = 2 / (n_periods + 1)
        self._bar_count = 0
        self._state = 0

    @property
    def ready(self) -> bool:
        return self._bar_count >= self._n_periods

    @property
    def value(self) -> np.float64:
        value = np.nan
        if self.ready:
            value = self._state
        return value

    def update(self, value: float):
        if self._bar_count >= self._n_periods:
            self._state = (value - self._state) * self._factor + self._state
        elif self._bar_count == self._n_periods - 1:
            self._state = (self._state + value) / self._n_periods
        else:  # self._bar_count < self._n_periods
            self._state += value

        self._bar_count += 1
