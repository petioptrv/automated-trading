import threading
import time

import pytest

from algotradepy.contracts import StockContract
from algotradepy.streamers.polygon_streamer import PolygonDataStreamer
from algotradepy.tick import Tick
from tests.conftest import PROJECT_DIR

API_TOKEN_FILE = PROJECT_DIR / "api_tokens" / "polygon-token.txt"
with open(API_TOKEN_FILE) as f:
    API_TOKEN = f.read()


@pytest.fixture()
def streamer():
    streamer = PolygonDataStreamer(api_token=API_TOKEN)

    yield streamer

    streamer.__del__()


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
