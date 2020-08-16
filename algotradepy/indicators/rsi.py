import numpy as np

from algotradepy.indicators.ma import SMA


class RSI:
    def __init__(self, n_periods: int):
        self._gain_sma = SMA(n_periods=n_periods)
        self._loss_sma = SMA(n_periods=n_periods)
        self._prev_val = None

    @property
    def ready(self) -> bool:
        return self._gain_sma.ready

    @property
    def value(self) -> np.float64:
        value = 100 - (100 / (1 + self._gain_sma.value / self._loss_sma.value))
        return np.float64(value)

    def update(self, value: float):
        if self._prev_val is not None:
            diff = value - self._prev_val
            gain_val = max(diff, 0)
            self._gain_sma.update(value=gain_val)
            loss_val = max(-diff, 0)
            self._loss_sma.update(value=loss_val)

        self._prev_val = value
