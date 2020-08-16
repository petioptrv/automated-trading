import time
from datetime import datetime, timedelta

import pytest

from algotradepy.contracts import StockContract, PriceType

AWAIT_TIME_OUT = 10


def get_streamer(client_id: int):
    pytest.importorskip("ib_insync")
    from algotradepy.connectors.ib_connector import build_and_start_connector
    from algotradepy.streamers.ib_streamer import IBDataStreamer

    conn = build_and_start_connector(client_id=client_id)
    streamer = IBDataStreamer(ib_connector=conn)

    return streamer


@pytest.fixture()
def streamer():
    pytest.importorskip("ib_insync")
    from algotradepy.connectors.ib_connector import MASTER_CLIENT_ID

    streamer = get_streamer(client_id=MASTER_CLIENT_ID)

    yield streamer

    streamer.__del__()


@pytest.mark.parametrize(
    "bar_size",
    [
        timedelta(seconds=5),
        timedelta(seconds=10),
        timedelta(minutes=1),
        timedelta(minutes=2),
    ],
)
def test_subscribe_to_bars_data(streamer, bar_size):
    latest = None

    def update(bar):
        nonlocal latest
        latest = bar

    contract = StockContract(symbol="SPY")
    streamer.subscribe_to_bars(
        contract=contract, bar_size=bar_size, func=update, rth=False,
    )

    streamer.sleep(bar_size.seconds + 10)

    assert latest is not None
    assert latest.name > datetime.now() - bar_size - timedelta(seconds=10)

    streamer.sleep(bar_size.seconds)

    assert latest is not None
    assert latest.name > datetime.now() - bar_size


def test_cancel_bars_data(streamer):
    latest = None

    def update(bar):
        nonlocal latest
        latest = bar

    contract = StockContract(symbol="SPY")
    streamer.subscribe_to_bars(
        contract=contract,
        bar_size=timedelta(seconds=5),
        func=update,
        rth=False,
    )

    streamer.sleep(15)

    assert latest is not None
    assert latest.name > datetime.now() - timedelta(seconds=15)

    streamer.cancel_bars(contract=contract, func=update)
    last_latest = latest
    streamer.sleep(15)

    assert last_latest.name == latest.name


def test_subscribe_to_tick_data(streamer):
    con = None
    ask = None
    bid = None
    mid = None

    def update_ask(contract_, price_):
        nonlocal con, ask
        con = contract_
        ask = price_

    def update_bid(c, price_):
        nonlocal bid
        bid = price_

    def update_mid(c, price_):
        nonlocal mid
        mid = price_

    contract = StockContract(symbol="SPY")
    streamer.subscribe_to_tick_data(
        contract=contract, func=update_ask, price_type=PriceType.ASK,
    )
    streamer.subscribe_to_tick_data(
        contract=contract, func=update_bid, price_type=PriceType.BID,
    )
    streamer.subscribe_to_tick_data(
        contract=contract, func=update_mid, price_type=PriceType.MARKET,
    )

    t0 = time.time()
    while (
        con is None
        and ask is None
        and bid is None
        and mid is None
        and time.time() - t0 <= AWAIT_TIME_OUT
    ):
        streamer.sleep()

    assert con == contract
    assert ask > bid
    assert mid == (ask + bid) / 2


def test_cancel_tick_data(streamer):
    mid = None

    def update_mid(c, price_):
        nonlocal mid
        mid = price_

    contract = StockContract(symbol="SPY")
    streamer.subscribe_to_tick_data(
        contract=contract, func=update_mid, price_type=PriceType.MARKET,
    )

    t0 = time.time()
    while mid is None and time.time() - t0 <= AWAIT_TIME_OUT:
        streamer.sleep()

    assert mid is not None

    mid = None
    t0 = time.time()
    while mid is None and time.time() - t0 <= AWAIT_TIME_OUT:
        streamer.sleep()

    assert mid is not None  # was refreshed

    streamer.cancel_tick_data(contract=contract, func=update_mid)
    streamer.sleep()
    mid = None
    t0 = time.time()
    while mid is None and time.time() - t0 <= AWAIT_TIME_OUT:
        streamer.sleep()

    assert mid is None  # did not refresh again
