import pytest

from algotradepy.orders import OrderAction, TrailingStopOrder


def test_trailing_stop_order_aux_price_and_trail_percent_fail():
    with pytest.raises(ValueError):
        TrailingStopOrder(
            action=OrderAction.BUY,
            quantity=1,
            trail_stop_price=10,
            aux_price=5,
            trail_percent=5,
        )

    with pytest.raises(ValueError):
        TrailingStopOrder(
            action=OrderAction.BUY,
            quantity=1,
            trail_stop_price=10,
            aux_price=None,
            trail_percent=None,
        )
