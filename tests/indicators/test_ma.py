import numpy as np
import pytest

from algotradepy.indicators.ma import SMA, EMA


@pytest.mark.parametrize(
    "ma,feed,targets",
    [
        (SMA(n_periods=3), [2, 3, 1, 5], [np.nan, np.nan, 2, 3]),
        (
            EMA(n_periods=10),
            [
                22.27,
                22.19,
                22.08,
                22.17,
                22.18,
                22.13,
                22.23,
                22.43,
                22.24,
                22.29,
                22.15,
                22.39,
                22.38,
                22.61,
                23.36,
                24.05,
                23.75,
                23.83,
                23.95,
                23.63,
                23.82,
                23.87,
                23.65,
                23.19,
                23.10,
                23.33,
                22.68,
                23.10,
                22.40,
                22.17,
            ],
            [
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                22.22,
                22.21,
                22.24,
                22.27,
                22.33,
                22.52,
                22.80,
                22.97,
                23.13,
                23.28,
                23.34,
                23.43,
                23.51,
                23.54,
                23.47,
                23.40,
                23.39,
                23.26,
                23.23,
                23.08,
                22.92,
            ],
        ),
    ],
)
def test_ma(ma, feed, targets):
    assert not ma.ready

    for val, target in zip(feed, targets):
        ma.update(val)
        assert (np.isnan(ma.value) and np.isnan(target)) or np.isclose(
            ma.value, target, 0.005
        )

    assert ma.ready
