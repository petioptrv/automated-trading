import pytest
import numpy as np

from algotradepy.brokers.sim_broker import SimulationBroker
from algotradepy.contracts import StockContract, Currency
from algotradepy.orders import MarketOrder, OrderAction, LimitOrder
from algotradepy.streamers.sim_streamer import SimulationDataStreamer
from algotradepy.trade import Trade, TradeState


def test_simulation_broker_init():
    spy_stock_contract = StockContract(symbol="SPY")
    streamer = SimulationDataStreamer()
    broker = SimulationBroker(
        sim_streamer=streamer,
        starting_funds={Currency.USD: 1_000},
        transaction_cost=1,
    )

    assert broker.acc_cash[Currency.USD] == 1_000
    assert broker.get_position(contract=spy_stock_contract) == 0
    assert broker.get_transaction_fee() == 1


def test_simulation_broker_buy(sim_broker_runner_and_streamer_15m):
    broker, runner, _ = sim_broker_runner_and_streamer_15m
    spy_stock_contract = StockContract(symbol="SPY")

    assert broker.get_position(contract=spy_stock_contract) == 0

    contract = StockContract(symbol="SPY")
    order = MarketOrder(action=OrderAction.BUY, quantity=1)
    trade = Trade(contract=contract, order=order)

    runner.run_sim(step_count=1, cache_only=True)
    broker.place_trade(trade=trade, order=order)

    spy_2020_4_6_9_45_open = 257.78

    assert np.isclose(
        broker.acc_cash[Currency.USD], 1000 - spy_2020_4_6_9_45_open - 1,
    )
    assert broker.get_position(contract=spy_stock_contract) == 1


def test_simulation_broker_sell(sim_broker_runner_and_streamer_15m):
    broker, runner, _ = sim_broker_runner_and_streamer_15m
    spy_stock_contract = StockContract(symbol="SPY")

    assert broker.get_position(contract=spy_stock_contract) == 0

    contract = StockContract(symbol="SPY")
    order = MarketOrder(action=OrderAction.SELL, quantity=1)
    trade = Trade(contract=contract, order=order)

    runner.run_sim(step_count=1)
    broker.place_trade(trade=trade, order=order)

    spy_2020_4_6_9_30_close = 257.77

    assert np.isclose(
        broker.acc_cash[Currency.USD],
        1000 + spy_2020_4_6_9_30_close - 1,
        0.01,
    )


def test_simulation_broker_limit_order(sim_broker_runner_and_streamer_15m):
    broker, runner, _ = sim_broker_runner_and_streamer_15m

    assert len(broker.open_trades) == 0

    contract = StockContract(symbol="SPY")
    order = LimitOrder(action=OrderAction.SELL, quantity=2, limit_price=99,)
    trade = Trade(contract=contract, order=order)

    runner.run_sim(step_count=1)
    _, trade = broker.place_trade(trade=trade, order=order)
    runner.run_sim(step_count=1)

    assert trade.status.state == TradeState.SUBMITTED

    broker.simulate_trade_execution(
        trade=trade, price=100, n_shares=1,
    )

    # does not update without sim step
    assert trade.status.state == TradeState.SUBMITTED

    runner.run_sim(step_count=1)

    assert trade.status.state == TradeState.FILLED
    assert trade.status.filled == 1
    assert trade.status.remaining == 1

    broker.simulate_trade_execution(
        trade=trade, price=100, n_shares=1,
    )

    runner.run_sim(step_count=1)

    assert trade.status.state == TradeState.FILLED
    assert trade.status.filled == 2
    assert trade.status.remaining == 0
