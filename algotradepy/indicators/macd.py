import numpy as np

from algotradepy.indicators.ma import EMA


class MACD:
    # TODO: test
    def __init__(
        self,
        short_ema_n_periods: int,
        long_ema_n_periods: int,
        signal_ema_n_periods: int,
    ):
        self._short_ema = EMA(n_periods=short_ema_n_periods)
        self._long_ema = EMA(n_periods=long_ema_n_periods)
        self._signal_ema = EMA(n_periods=signal_ema_n_periods)

    @property
    def macd_line(self) -> np.float64:
        value = np.nan
        if self._short_ema.ready and self._long_ema.ready:
            value = self._short_ema.value - self._long_ema.value
        return value

    @property
    def signal_line(self) -> np.float64:
        value = self._signal_ema.value
        return value

    @property
    def macd_hist(self) -> np.float64:
        value = np.nan
        sl = self.signal_line
        if not np.isnan(sl):
            ml = self.macd_line
            value = ml - sl
        return value

    def update(self, value: float):
        self._short_ema.update(value=value)
        self._long_ema.update(value=value)

        macd_val = self.macd_line
        if not np.isnan(macd_val):
            self._signal_ema.update(value=macd_val)
