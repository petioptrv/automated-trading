from datetime import date, timedelta

import numpy as np
import pytest

from algotradepy.brokers import SimulationBroker
from algotradepy.contracts import StockContract, Currency, PriceType
from algotradepy.historical.loaders import HistoricalRetriever
from algotradepy.sim_utils import SimulationClock, SimulationRunner
from algotradepy.streamers.sim_streamer import SimulationDataStreamer
from tests.conftest import TEST_DATA_DIR


class BarChecker:
    def __init__(self, start_date: date, end_date: date, bar_size: timedelta):
        hist_retriever = HistoricalRetriever(hist_data_dir=TEST_DATA_DIR)
        contract = StockContract(symbol="SPY")
        self._sim_data = hist_retriever.retrieve_bar_data(
            contract=contract,
            bar_size=bar_size,
            start_date=start_date,
            end_date=end_date,
            cache_only=True,
        )
        self._sim_idx = 0

    def bar_receiver(self, bar):
        assert np.all(bar == self._sim_data.iloc[self._sim_idx])
        self._sim_idx += 1

    def assert_all_received(self):
        assert self._sim_idx == len(self._sim_data)


def test_simulation_broker_register_same_bar_size(
    sim_broker_runner_and_streamer_15m,
):
    _, runner, streamer = sim_broker_runner_and_streamer_15m
    checker = BarChecker(
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 7),
        bar_size=timedelta(minutes=15),
    )
    contract = StockContract(symbol="SPY")
    streamer.subscribe_to_bars(
        contract=contract,
        bar_size=timedelta(minutes=15),
        func=checker.bar_receiver,
    )
    runner.run_sim()
    checker.assert_all_received()


def test_simulation_broker_register_diff_bar_size(
    sim_broker_runner_and_streamer_15m,
):
    _, runner, streamer = sim_broker_runner_and_streamer_15m
    checker = BarChecker(
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 7),
        bar_size=timedelta(minutes=30),
    )
    contract = StockContract(symbol="SPY")
    streamer.subscribe_to_bars(
        contract=contract,
        bar_size=timedelta(minutes=30),
        func=checker.bar_receiver,
    )
    runner.run_sim()
    checker.assert_all_received()


def test_simulation_broker_register_daily(sim_broker_runner_and_streamer_15m):
    _, runner, streamer = sim_broker_runner_and_streamer_15m
    checker = BarChecker(
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 7),
        bar_size=timedelta(days=1),
    )
    contract = StockContract(symbol="SPY")
    streamer.subscribe_to_bars(
        contract=contract,
        bar_size=timedelta(days=1),
        func=checker.bar_receiver,
    )
    runner.run_sim()
    checker.assert_all_received()


def test_simulation_broker_register_tick_resolution_fail(
    sim_broker_runner_and_streamer_15m,
):
    spy_stock_contract = StockContract(symbol="SPY")
    _, _, streamer = sim_broker_runner_and_streamer_15m
    with pytest.raises(ValueError):
        streamer.subscribe_to_tick_data(
            contract=spy_stock_contract, func=lambda x: None,
        )


@pytest.fixture
def sim_broker_runner_and_streamer_1s():
    sim_clock = SimulationClock(
        start_date=date(2020, 6, 17),
        end_date=date(2020, 6, 17),
        simulation_time_step=timedelta(seconds=1),
    )
    streamer = SimulationDataStreamer(
        historical_retriever=HistoricalRetriever(hist_data_dir=TEST_DATA_DIR),
    )
    broker = SimulationBroker(
        sim_streamer=streamer,
        starting_funds={Currency.USD: 1_000},
        transaction_cost=1,
    )
    sim_runner = SimulationRunner(
        sim_clock=sim_clock,
        data_providers=[streamer],
        data_consumers=[broker],
    )
    return broker, sim_runner, streamer


def test_simulation_broker_register_tick_single_symbol(
    sim_broker_runner_and_streamer_1s,
):
    spy_stock_contract = StockContract(symbol="SPY")
    _, runner, streamer = sim_broker_runner_and_streamer_1s

    mkt_prices = []
    ask_prices = []
    bid_prices = []

    def mkt_receiver(_, price):
        nonlocal mkt_prices
        mkt_prices.append(price)

    def ask_receiver(_, price):
        nonlocal ask_prices
        ask_prices.append(price)

    def bid_receiver(_, price):
        nonlocal bid_prices
        bid_prices.append(price)

    streamer.subscribe_to_tick_data(
        contract=spy_stock_contract, func=mkt_receiver,
    )
    streamer.subscribe_to_tick_data(
        contract=spy_stock_contract,
        func=ask_receiver,
        price_type=PriceType.ASK,
    )
    streamer.subscribe_to_tick_data(
        contract=spy_stock_contract,
        func=bid_receiver,
        price_type=PriceType.BID,
    )

    runner.run_sim(step_count=4)

    np.testing.assert_equal(mkt_prices, [409.99, 410.385])
    np.testing.assert_equal(ask_prices, [413.53, 411.52])
    np.testing.assert_equal(bid_prices, [406.45, 409.25])


def test_simulation_broker_register_tick_multi_symbol(
    sim_broker_runner_and_streamer_1s,
):
    _, runner, streamer = sim_broker_runner_and_streamer_1s
    spy_stock_contract = StockContract(symbol="SPY")
    schw_stock_contract = StockContract(symbol="SCHW")

    spy_ask = []
    schw_ask = []

    def spy_receiver(_, price):
        nonlocal spy_ask
        spy_ask.append(price)

    def schw_receiver(_, price):
        nonlocal schw_ask
        schw_ask.append(price)

    streamer.subscribe_to_tick_data(
        contract=spy_stock_contract,
        func=spy_receiver,
        price_type=PriceType.ASK,
    )
    streamer.subscribe_to_tick_data(
        contract=schw_stock_contract,
        func=schw_receiver,
        price_type=PriceType.ASK,
    )

    runner.run_sim(step_count=4)

    np.testing.assert_equal(spy_ask, [413.53, 411.52])
    np.testing.assert_equal(schw_ask, [37.442, 37.442])


def test_cancel_tick_data(sim_broker_runner_and_streamer_1s):
    _, runner, streamer = sim_broker_runner_and_streamer_1s
    spy_stock_contract = StockContract(symbol="SPY")
    schw_stock_contract = StockContract(symbol="SCHW")

    spy_ask = []
    schw_ask = []

    def spy_receiver(_, price):
        nonlocal spy_ask
        spy_ask.append(price)

    def schw_receiver(_, price):
        nonlocal schw_ask
        schw_ask.append(price)

    streamer.subscribe_to_tick_data(
        contract=spy_stock_contract,
        func=spy_receiver,
        price_type=PriceType.ASK,
    )
    streamer.subscribe_to_tick_data(
        contract=schw_stock_contract,
        func=schw_receiver,
        price_type=PriceType.ASK,
    )

    runner.run_sim(step_count=2)
    streamer.cancel_tick_data(
        contract=spy_stock_contract, func=spy_receiver,
    )
    runner.run_sim(step_count=2)

    np.testing.assert_equal(spy_ask, [413.53])
    np.testing.assert_equal(schw_ask, [37.442, 37.442])


def test_tick_data_delivery_order(sim_broker_runner_and_streamer_1s):
    _, runner, streamer = sim_broker_runner_and_streamer_1s
    spy_stock_contract = StockContract(symbol="SPY")
    schw_stock_contract = StockContract(symbol="SCHW")

    spy_ask = []
    schw_ask = []

    def spy_receiver(_, price):
        nonlocal spy_ask, schw_ask
        spy_ask.append(price)
        if price == 406.9:
            assert abs(len(spy_ask) - len(schw_ask)) == 0
        elif price == 407.57:
            assert abs(len(spy_ask) - len(schw_ask)) == 0

    def schw_receiver(_, price):
        nonlocal schw_ask
        schw_ask.append(price)

    streamer.subscribe_to_tick_data(
        contract=spy_stock_contract,
        func=spy_receiver,
        price_type=PriceType.ASK,
    )
    streamer.subscribe_to_tick_data(
        contract=schw_stock_contract,
        func=schw_receiver,
        price_type=PriceType.ASK,
    )

    runner.run_sim(step_count=9)

    assert len(spy_ask) == 17
    assert len(schw_ask) == 18
