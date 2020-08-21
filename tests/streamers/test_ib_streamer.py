import time
from datetime import datetime, timedelta

import pytest
import numpy as np

from algotradepy.contracts import (
    StockContract,
    PriceType,
    OptionContract,
    Right,
)
from algotradepy.objects import Greeks

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

    prev = latest.copy()
    latest = None
    streamer.sleep(bar_size.seconds)

    assert latest is not None
    assert latest.name > datetime.now() - bar_size
    assert latest.name > prev.name


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


def get_valid_spy_contract(idx) -> OptionContract:
    from ib_insync import IB, Stock

    ib = IB()
    ib.connect(clientId=idx + 1)
    ib_stk_con = Stock(symbol="SPY", exchange="SMART", currency="USD")
    ib_details = ib.reqContractDetails(ib_stk_con)[0]
    ib.reqMarketDataType(4)
    tick = ib.reqMktData(contract=ib_stk_con, snapshot=True)
    while np.isnan(tick.ask):
        ib.sleep()
    ask = tick.ask
    ib_con_id = ib_details.contract.conId
    ib_chains = ib.reqSecDefOptParams(
        underlyingSymbol="SPY",
        futFopExchange="",
        underlyingSecType="STK",
        underlyingConId=ib_con_id,
    )
    ib_chain = ib_chains[0]
    ib_chain.strikes.sort(key=lambda s: abs(s - ask))
    strike = ib_chain.strikes[0]
    expiration_str = ib_chain.expirations[idx]
    expiration_date = datetime.strptime(expiration_str, "%Y%m%d")
    spy_contract = OptionContract(
        symbol="SPY",
        strike=strike,
        right=Right.CALL,
        multiplier=int(ib_chain.multiplier),
        last_trade_date=expiration_date,
    )
    ib.disconnect()

    return spy_contract


@pytest.fixture()
def first_valid_spy_option() -> OptionContract:
    pytest.importorskip("ib_insync")
    con = get_valid_spy_contract(idx=0)
    return con


@pytest.fixture()
def second_valid_spy_option() -> OptionContract:
    pytest.importorskip("ib_insync")
    con = get_valid_spy_contract(idx=1)
    return con


def test_subscribe_to_greeks(
    streamer, first_valid_spy_option, second_valid_spy_option,
):
    first_greek_updates = []
    second_greek_updates = []

    def update_first_greeks(greeks: Greeks):
        first_greek_updates.append(greeks)

    def update_second_greeks(greeks: Greeks):
        second_greek_updates.append(greeks)

    streamer.subscribe_to_greeks(
        contract=first_valid_spy_option, func=update_first_greeks,
    )
    streamer.subscribe_to_greeks(
        contract=second_valid_spy_option, func=update_second_greeks,
    )

    while len(first_greek_updates) == 0 or len(second_greek_updates) == 0:
        streamer.sleep()

    assert isinstance(first_greek_updates[0], Greeks)
    assert first_greek_updates[-1] != second_greek_updates[-1]


def test_cancel_greeks(streamer, first_valid_spy_option):
    greek_updates = []

    def update_greeks(greeks: Greeks):
        greek_updates.append(greeks)

    streamer.subscribe_to_greeks(
        contract=first_valid_spy_option, func=update_greeks,
    )

    while len(greek_updates) == 0:
        streamer.sleep()

    streamer.cancel_greeks(
        contract=first_valid_spy_option, func=update_greeks,
    )

    streamer.sleep(1)
    first_len = len(greek_updates)
    streamer.sleep(5)

    assert len(greek_updates) == first_len
