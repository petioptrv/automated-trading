import numpy as np

from algotradepy.indicators.rsi import RSI


def test_rsi():
    rsi = RSI(n_periods=14)

    feed = [
        1.6125,
        1.6151,
        1.6128,
        1.6151,
        1.6128,
        1.6057,
        1.5991,
        1.5964,
        1.5979,
        1.6017,
        1.602,
        1.6114,
        1.6124,
        1.6223,
        1.6295,
        1.63,
    ]
    targets = [
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        64.406779661017,
        63.093145869947,
    ]

    for i in range(len(feed)):
        rsi.update(value=feed[i])
        assert (np.isnan(rsi.value) and np.isnan(targets[i])) or np.isclose(
            rsi.value, targets[i], 0.005
        )
