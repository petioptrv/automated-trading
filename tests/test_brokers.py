from datetime import date, timedelta, time, datetime
import time as real_time

import pytest
import numpy as np

from algotradepy.brokers import (
    SimulationBroker,
    SimulationClock,
    SimulationEndException,
)
from algotradepy.historical.loaders import HistoricalRetriever
from tests.conftest import TEST_DATA_DIR


def test_simulation_clock_single_day_1min_res():
    clock = SimulationClock(
        start_date=date(2020, 1, 2),
        end_date=date(2020, 1, 2),
        simulation_time_step=timedelta(minutes=1),
    )

    assert clock.date == date(2020, 1, 2)
    assert clock.time == time(9, 30)

    [clock.tick() for _ in range(389)]

    assert clock.time == time(15, 59)
    with pytest.raises(SimulationEndException):
        clock.tick()


def test_simulation_clock_single_day_10min_res():
    clock = SimulationClock(
        start_date=date(2020, 1, 2),
        end_date=date(2020, 1, 2),
        simulation_time_step=timedelta(minutes=10),
    )

    [clock.tick() for _ in range(38)]

    assert clock.time == time(15, 50)
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

    with pytest.raises(SimulationEndException):
        [clock.tick() for _ in range(13)]

    t2 = real_time.time()

    assert np.isclose(t2 - t1, 13, atol=.1)


def test_simulation_clock_multi_day():
    clock = SimulationClock(
        start_date=date(2020, 1, 2),
        end_date=date(2020, 1, 3),
        simulation_time_step=timedelta(minutes=30),
    )

    [clock.tick() for _ in range(25)]

    assert clock.time == time(15, 30)
    assert clock.date == date(2020, 1, 3)
    with pytest.raises(SimulationEndException):
        clock.tick()


def test_simulation_clock_multi_day_weekend():
    clock = SimulationClock(
        start_date=date(2020, 1, 3),
        end_date=date(2020, 1, 6),
        simulation_time_step=timedelta(minutes=30),
    )

    [clock.tick() for _ in range(25)]

    assert clock.time == time(15, 30)
    assert clock.date == date(2020, 1, 6)
    with pytest.raises(SimulationEndException):
        clock.tick()


def test_simulation_clock_daily():
    clock = SimulationClock(
        start_date=date(2020, 1, 6),
        end_date=date(2020, 1, 8),
        simulation_time_step=timedelta(days=1),
    )

    [clock.tick() for _ in range(2)]

    assert clock.time == time(9, 30)
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


def test_simulation_broker_init():
    sim_clock = SimulationClock(
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 6),
        simulation_time_step=timedelta(minutes=15),
    )
    broker = SimulationBroker(
        starting_funds=1_000,
        transaction_cost=1,
        sim_clock=sim_clock,
        hist_retriever=HistoricalRetriever(hist_data_dir=TEST_DATA_DIR),
    )

    assert broker.acc_cash == 1_000
    assert broker.get_position("SPY") == 0
    assert broker.get_transaction_fee() == 1


@pytest.fixture
def sim_broker():
    sim_clock = SimulationClock(
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 6),
        simulation_time_step=timedelta(minutes=15),
    )
    broker = SimulationBroker(
        starting_funds=1_000,
        transaction_cost=1,
        sim_clock=sim_clock,
        hist_retriever=HistoricalRetriever(hist_data_dir=TEST_DATA_DIR),
    )
    return broker


def test_simulation_broker_buy(sim_broker):
    broker = sim_broker

    assert broker.get_position("SPY") == 0

    broker.buy(symbol="SPY", n_shares=1)

    spy_2020_4_6_9_30_close = 257.77

    assert np.isclose(
        broker.acc_cash,
        1000 - spy_2020_4_6_9_30_close - 1,
    )
    assert broker.get_position("SPY") == 1


def test_simulation_broker_sell(sim_broker):
    broker = sim_broker

    assert broker.get_position("SPY") == 0

    broker.sell(symbol="SPY", n_shares=1)

    spy_2020_4_6_9_30_close = 257.77

    assert np.isclose(
        broker.acc_cash,
        1000 + spy_2020_4_6_9_30_close - 1,
        .01,
    )


@pytest.fixture
def bar_checker():
    hist_retriever = HistoricalRetriever(hist_data_dir=TEST_DATA_DIR)
    sim_data = hist_retriever.retrieve_bar_data(
        symbol="SPY",
        bar_size=timedelta(minutes=15),
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 6),
        cache_only=True,
    )

    sim_idx = 0

    def step(bar):
        nonlocal sim_idx
        assert np.all(bar == sim_data.iloc[sim_idx])
        sim_idx += 1

    return step


def test_simulation_broker_register_same_bar_size(sim_broker, bar_checker):
    sim_broker.register_for_bars(
        symbol="SPY",
        bar_size=timedelta(minutes=15),
        func=bar_checker,
    )
    sim_broker.run_sim()
