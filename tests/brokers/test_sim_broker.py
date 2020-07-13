from datetime import date, timedelta, time, datetime
import time as real_time

import pytest
import numpy as np

from algotradepy.brokers.sim_broker import (
    SimulationBroker,
    SimulationClock,
    SimulationEndException,
)
from algotradepy.contracts import StockContract, PriceType
from algotradepy.historical.loaders import HistoricalRetriever
from algotradepy.orders import MarketOrder, OrderAction
from tests.conftest import TEST_DATA_DIR


def test_simulation_clock_single_day_1min_res():
    clock = SimulationClock(
        start_date=date(2020, 1, 2),
        end_date=date(2020, 1, 2),
        simulation_time_step=timedelta(minutes=1),
    )

    assert clock.date == date(2020, 1, 2)
    assert clock.time == time(9, 30)

    [clock.tick() for _ in range(390)]

    assert clock.time == time(16)
    with pytest.raises(SimulationEndException):
        clock.tick()


def test_simulation_clock_single_day_10min_res():
    clock = SimulationClock(
        start_date=date(2020, 1, 2),
        end_date=date(2020, 1, 2),
        simulation_time_step=timedelta(minutes=10),
    )

    [clock.tick() for _ in range(39)]

    assert clock.time == time(16)
    with pytest.raises(SimulationEndException):
        clock.tick()


def test_simulation_clock_real_time():
    clock = SimulationClock(
        start_date=date(2020, 1, 2),
        end_date=date(2020, 1, 2),
        simulation_time_step=timedelta(minutes=30),
        real_time_per_tick=1,
    )

    t1 = real_time.time()

    [clock.tick() for _ in range(2)]

    t2 = real_time.time()

    assert np.isclose(t2 - t1, 2, atol=0.1)


def test_simulation_clock_multi_day():
    clock = SimulationClock(
        start_date=date(2020, 1, 2),
        end_date=date(2020, 1, 3),
        simulation_time_step=timedelta(minutes=30),
    )

    [clock.tick() for _ in range(26)]

    assert clock.time == time(16)
    assert clock.date == date(2020, 1, 3)
    with pytest.raises(SimulationEndException):
        clock.tick()


def test_simulation_clock_multi_day_weekend():
    clock = SimulationClock(
        start_date=date(2020, 1, 3),
        end_date=date(2020, 1, 6),
        simulation_time_step=timedelta(minutes=30),
    )

    [clock.tick() for _ in range(26)]

    assert clock.time == time(16)
    assert clock.date == date(2020, 1, 6)
    with pytest.raises(SimulationEndException):
        clock.tick()


def test_simulation_clock_daily():
    clock = SimulationClock(
        start_date=date(2020, 1, 6),
        end_date=date(2020, 1, 8),
        simulation_time_step=timedelta(days=1),
    )

    [clock.tick() for _ in range(3)]

    assert clock.time == time(16)
    assert clock.date == date(2020, 1, 8)
    with pytest.raises(SimulationEndException):
        clock.tick()


@pytest.fixture
def sim_clock():
    c = SimulationClock(
        start_date=date(2020, 1, 6),
        end_date=date(2020, 1, 8),
        simulation_time_step=timedelta(minutes=1),
    )
    return c


def test_simulation_clock_advance_time(sim_clock):
    sim_clock.set_datetime(datetime(2020, 1, 6, 10))

    assert sim_clock.date == date(2020, 1, 6)
    assert sim_clock.time == time(10)


def test_simulation_clock_reverse_time(sim_clock):
    sim_clock.set_datetime(datetime(2020, 1, 6, 10))
    sim_clock.set_datetime(datetime(2020, 1, 6, 9, 30))

    assert sim_clock.time == time(9, 30)


def test_simulation_clock_advance_date(sim_clock):
    sim_clock.set_datetime(datetime(2020, 1, 7, 11))

    assert sim_clock.date == date(2020, 1, 7)
    assert sim_clock.time == time(11)


def test_simulation_clock_reverse_date(sim_clock):
    sim_clock.set_datetime(datetime(2020, 1, 7, 9, 30))
    sim_clock.set_datetime(datetime(2020, 1, 6, 9, 30))

    assert sim_clock.date == date(2020, 1, 6)

    with pytest.raises(ValueError):
        sim_clock.set_datetime(datetime(2019, 1, 8))

    with pytest.raises(ValueError):
        sim_clock.set_datetime(datetime(2020, 1, 8, 10, 0, 30))

    with pytest.raises(ValueError):
        sim_clock.set_datetime(datetime(2020, 1, 8, 8))


@pytest.fixture()
def spy_stock_contract():
    contract = StockContract(symbol="SPY")
    return contract


def test_simulation_broker_init(spy_stock_contract):
    broker = SimulationBroker(
        starting_funds=1_000,
        transaction_cost=1,
        hist_retriever=HistoricalRetriever(hist_data_dir=TEST_DATA_DIR),
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 6),
        simulation_time_step=timedelta(minutes=15),
    )

    assert broker.acc_cash == 1_000
    assert broker.get_position(contract=spy_stock_contract) == 0
    assert broker.get_transaction_fee() == 1


@pytest.fixture
def sim_broker_15m():
    broker = SimulationBroker(
        starting_funds=1_000,
        transaction_cost=1,
        hist_retriever=HistoricalRetriever(hist_data_dir=TEST_DATA_DIR),
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 7),
        simulation_time_step=timedelta(minutes=15),
    )
    return broker


def test_simulation_broker_buy(sim_broker_15m, spy_stock_contract):
    broker = sim_broker_15m

    assert broker.get_position(contract=spy_stock_contract) == 0

    contract = StockContract(symbol="SPY")
    order = MarketOrder(action=OrderAction.BUY, quantity=1)

    broker._clock.tick()  # TODO: remove use of implementation details
    broker.place_trade(contract=contract, order=order)

    spy_2020_4_6_9_45_open = 257.78

    assert np.isclose(broker.acc_cash, 1000 - spy_2020_4_6_9_45_open - 1,)
    assert broker.get_position(contract=spy_stock_contract) == 1


def test_simulation_broker_sell(sim_broker_15m):
    broker = sim_broker_15m

    assert broker.get_position(contract=spy_stock_contract) == 0

    contract = StockContract(symbol="SPY")
    order = MarketOrder(action=OrderAction.SELL, quantity=1)

    broker._clock.tick()  # TODO: remove use of implementation details
    broker.place_trade(contract=contract, order=order)

    spy_2020_4_6_9_30_close = 257.77

    assert np.isclose(
        broker.acc_cash, 1000 + spy_2020_4_6_9_30_close - 1, 0.01,
    )


class BarChecker:
    def __init__(self, start_date: date, end_date: date, bar_size: timedelta):
        hist_retriever = HistoricalRetriever(hist_data_dir=TEST_DATA_DIR)
        self._sim_data = hist_retriever.retrieve_bar_data(
            symbol="SPY",
            bar_size=bar_size,
            start_date=start_date,
            end_date=end_date,
            cache_only=True,
        )
        self._sim_idx = 0

    def step(self, bar):
        assert np.all(bar == self._sim_data.iloc[self._sim_idx])
        self._sim_idx += 1

    def assert_all_received(self):
        assert self._sim_idx == len(self._sim_data)


def test_simulation_broker_register_same_bar_size(sim_broker_15m):
    checker = BarChecker(
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 7),
        bar_size=timedelta(minutes=15),
    )
    sim_broker_15m.subscribe_to_bars(
        symbol="SPY", bar_size=timedelta(minutes=15), func=checker.step,
    )
    sim_broker_15m.run_sim()
    checker.assert_all_received()


def test_simulation_broker_register_diff_bar_size(sim_broker_15m):
    checker = BarChecker(
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 7),
        bar_size=timedelta(minutes=30),
    )
    sim_broker_15m.subscribe_to_bars(
        symbol="SPY", bar_size=timedelta(minutes=30), func=checker.step,
    )
    sim_broker_15m.run_sim()
    checker.assert_all_received()


def test_simulation_broker_register_daily(sim_broker_15m):
    checker = BarChecker(
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 7),
        bar_size=timedelta(days=1),
    )
    sim_broker_15m.subscribe_to_bars(
        symbol="SPY", bar_size=timedelta(days=1), func=checker.step,
    )
    sim_broker_15m.run_sim()
    checker.assert_all_received()


def test_simulation_broker_register_tick_resolution_fail(
    sim_broker_15m, spy_stock_contract,
):
    with pytest.raises(ValueError):
        sim_broker_15m.subscribe_to_tick_data(
            contract=spy_stock_contract, func=lambda x: None,
        )


@pytest.fixture
def sim_broker_1s():
    broker = SimulationBroker(
        starting_funds=1_000,
        transaction_cost=1,
        hist_retriever=HistoricalRetriever(hist_data_dir=TEST_DATA_DIR),
        start_date=date(2020, 6, 17),
        end_date=date(2020, 6, 17),
        simulation_time_step=timedelta(seconds=1),
    )
    return broker


def test_simulation_broker_register_tick_single_symbol(
    sim_broker_1s, spy_stock_contract,
):
    mkt_prices = []
    ask_prices = []
    bid_prices = []

    def mkt_receiver(contract, price):
        nonlocal mkt_prices
        mkt_prices.append(price)

    def ask_receiver(contract, price):
        nonlocal ask_prices
        ask_prices.append(price)

    def bid_receiver(contract, price):
        nonlocal bid_prices
        bid_prices.append(price)

    sim_broker_1s.subscribe_to_tick_data(
        contract=spy_stock_contract, func=mkt_receiver,
    )
    sim_broker_1s.subscribe_to_tick_data(
        contract=spy_stock_contract,
        func=ask_receiver,
        price_type=PriceType.ASK,
    )
    sim_broker_1s.subscribe_to_tick_data(
        contract=spy_stock_contract,
        func=bid_receiver,
        price_type=PriceType.BID,
    )

    sim_broker_1s.run_sim(step_count=3)

    np.testing.assert_equal(mkt_prices, [409.99, 410.385])
    np.testing.assert_equal(ask_prices, [413.53, 411.52])
    np.testing.assert_equal(bid_prices, [406.45, 409.25])


@pytest.fixture()
def schw_stock_contract():
    contract = StockContract(symbol="SCHW")
    return contract


def test_simulation_broker_register_tick_multi_symbol(
    sim_broker_1s, spy_stock_contract, schw_stock_contract,
):
    spy_ask = []
    schw_ask = []

    def spy_receiver(_, price):
        nonlocal spy_ask
        spy_ask.append(price)

    def schw_receiver(_, price):
        nonlocal schw_ask
        schw_ask.append(price)

    sim_broker_1s.subscribe_to_tick_data(
        contract=spy_stock_contract,
        func=spy_receiver,
        price_type=PriceType.ASK,
    )
    sim_broker_1s.subscribe_to_tick_data(
        contract=schw_stock_contract,
        func=schw_receiver,
        price_type=PriceType.ASK,
    )

    sim_broker_1s.run_sim(step_count=3)

    np.testing.assert_equal(spy_ask, [413.53, 411.52])
    np.testing.assert_equal(schw_ask, [37.442, 37.442])


def test_cancel_tick_data(
    sim_broker_1s, spy_stock_contract, schw_stock_contract,
):
    spy_ask = []
    schw_ask = []

    def spy_receiver(_, price):
        nonlocal spy_ask
        spy_ask.append(price)

    def schw_receiver(_, price):
        nonlocal schw_ask
        schw_ask.append(price)

    sim_broker_1s.subscribe_to_tick_data(
        contract=spy_stock_contract,
        func=spy_receiver,
        price_type=PriceType.ASK,
    )
    sim_broker_1s.subscribe_to_tick_data(
        contract=schw_stock_contract,
        func=schw_receiver,
        price_type=PriceType.ASK,
    )

    sim_broker_1s.run_sim(step_count=2)
    sim_broker_1s.cancel_tick_data(
        contract=spy_stock_contract, func=spy_receiver,
    )
    sim_broker_1s.run_sim(step_count=1)

    np.testing.assert_equal(spy_ask, [413.53])
    np.testing.assert_equal(schw_ask, [37.442, 37.442])


def test_tick_data_delivery_order(
    sim_broker_1s, spy_stock_contract, schw_stock_contract,
):
    spy_ask = []
    schw_ask = []

    def spy_receiver(_, price):
        nonlocal spy_ask, schw_ask
        spy_ask.append(price)
        if price == 406.9:
            assert abs(len(spy_ask) - len(schw_ask)) == 0
        elif price == 407.57:
            assert abs(len(spy_ask) - len(schw_ask)) == 1

    def schw_receiver(_, price):
        nonlocal schw_ask
        schw_ask.append(price)

    sim_broker_1s.subscribe_to_tick_data(
        contract=spy_stock_contract,
        func=spy_receiver,
        price_type=PriceType.ASK,
    )
    sim_broker_1s.subscribe_to_tick_data(
        contract=schw_stock_contract,
        func=schw_receiver,
        price_type=PriceType.ASK,
    )

    sim_broker_1s.run_sim(step_count=8)

    assert len(spy_ask) == 17
    assert len(schw_ask) == 18
