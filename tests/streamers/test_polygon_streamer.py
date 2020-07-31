import threading
import time

import pytest

from algotradepy.contracts import StockContract
from algotradepy.tick import Tick
from tests.conftest import can_test_polygon


@pytest.fixture()
def streamer(polygon_api_token):
    from algotradepy.streamers.polygon_streamer import PolygonDataStreamer

    streamer = PolygonDataStreamer(api_token=polygon_api_token)

    yield streamer

    streamer.__del__()


@pytest.mark.skipif(not can_test_polygon(), reason="Polygon not available.")
def test_subscribe_to_trades_data(streamer):
    tick = None
    received = threading.Event()

    def receiver(t):
        nonlocal tick
        nonlocal received

        if not received.is_set():
            tick = t
            received.set()

    streamer.subscribe_to_trades(
        contract=StockContract(symbol="SPY"), func=receiver,
    )

    received.wait(2)

    assert isinstance(tick, Tick)
    assert tick.symbol == "SPY"


@pytest.mark.skipif(not can_test_polygon(), reason="Polygon not available.")
def test_cancel_trades_data(streamer):
    tick = None
    received = threading.Event()

    def receiver(t):
        nonlocal tick
        nonlocal received

        tick = t
        if not received.is_set():
            received.set()

    streamer.subscribe_to_trades(
        contract=StockContract(symbol="SPY"), func=receiver,
    )

    received.wait(1)

    assert tick is not None

    tick = None

    time.sleep(1)

    assert tick is not None

    streamer.cancel_trades(
        contract=StockContract(symbol="SPY"), func=receiver,
    )

    time.sleep(1)

    tick = None

    time.sleep(1)

    assert tick is None
