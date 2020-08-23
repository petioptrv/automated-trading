import pytest
import numpy as np

from algotradepy.brokers.sim_broker import SimulationBroker, DEFAULT_SIM_ACC
from algotradepy.contracts import StockContract, Currency
from algotradepy.objects import Position
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


def get_1_spy_mkt_trade(buy: bool) -> Trade:
    contract = StockContract(symbol="SPY")

    if buy:
        action = OrderAction.BUY
    else:
        action = OrderAction.SELL

    order = MarketOrder(action=action, quantity=1)
    trade = Trade(contract=contract, order=order)

    return trade


@pytest.fixture()
def buy_1_spy_mkt_trade() -> Trade:
    trade = get_1_spy_mkt_trade(buy=True)
    return trade


@pytest.fixture()
def sell_1_spy_mkt_trade() -> Trade:
    trade = get_1_spy_mkt_trade(buy=False)
    return trade


def test_simulation_broker_buy(
    sim_broker_runner_and_streamer_15m, buy_1_spy_mkt_trade,
):
    broker, runner, _ = sim_broker_runner_and_streamer_15m
    spy_stock_contract = StockContract(symbol="SPY")

    assert broker.get_position(contract=spy_stock_contract) == 0

    runner.run_sim(step_count=1, cache_only=True)

    broker.place_trade(trade=buy_1_spy_mkt_trade)

    runner.run_sim(step_count=1, cache_only=True)

    spy_2020_4_6_9_45_open = 259.79

    assert np.isclose(
        broker.acc_cash[Currency.USD], 1000 - spy_2020_4_6_9_45_open - 1,
    )
    assert broker.get_position(contract=spy_stock_contract) == 1


def test_simulation_broker_sell(
    sim_broker_runner_and_streamer_15m, sell_1_spy_mkt_trade,
):
    broker, runner, _ = sim_broker_runner_and_streamer_15m
    spy_stock_contract = StockContract(symbol="SPY")

    assert broker.get_position(contract=spy_stock_contract) == 0

    runner.run_sim(step_count=1)

    broker.place_trade(trade=sell_1_spy_mkt_trade)

    runner.run_sim(step_count=1)

    spy_2020_4_6_9_30_close = 259.79

    assert np.isclose(
        broker.acc_cash[Currency.USD],
        1000 + spy_2020_4_6_9_30_close - 1,
        0.01,
    )


def test_open_trades(
    sim_broker_runner_and_streamer_15m, buy_1_spy_mkt_trade,
):
    broker, _, _ = sim_broker_runner_and_streamer_15m

    assert len(broker.open_trades) == 0

    broker.place_trade(trade=buy_1_spy_mkt_trade)

    assert len(broker.open_trades) == 1

    trade = broker.open_trades[0]

    assert trade == buy_1_spy_mkt_trade


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


def test_subscribe_to_position_updates():
    con = StockContract(symbol="SPY")
    pos = Position(
        account=DEFAULT_SIM_ACC,
        contract=con,
        position=10,
        ave_fill_price=345.6,
    )
    starting_positions = {
        DEFAULT_SIM_ACC: {con: pos},
    }
    untethered_sim_broker = SimulationBroker(
        sim_streamer=SimulationDataStreamer(),
        starting_funds={Currency.USD: 10_000},
        transaction_cost=1,
        starting_positions=starting_positions,
    )

    pos_updates = []

    def pos_updates_receiver(pos_: Position):
        pos_updates.append(pos_)

    untethered_sim_broker.subscribe_to_position_updates(
        func=pos_updates_receiver,
    )
    sim_order = LimitOrder(action=OrderAction.BUY, quantity=2, limit_price=346)
    sim_trade = Trade(contract=con, order=sim_order)
    untethered_sim_broker.place_trade(trade=sim_trade)
    untethered_sim_broker.simulate_trade_execution(
        trade=sim_trade, price=345.8, n_shares=1,
    )
    untethered_sim_broker.step()

    assert len(pos_updates) == 1

    updated_pos: Position = pos_updates[0]
    target_ave_price = (10 * 345.6 + 345.8) / 11

    assert updated_pos.contract == con
    assert updated_pos.position == 11
    assert updated_pos.ave_fill_price == target_ave_price
    assert updated_pos.account == DEFAULT_SIM_ACC

    untethered_sim_broker.simulate_trade_execution(
        trade=sim_trade, price=345.9, n_shares=1,
    )
    untethered_sim_broker.step()

    updated_pos: Position = pos_updates[1]
    target_ave_price = (target_ave_price * 11 + 345.9) / 12

    assert updated_pos.contract == con
    assert updated_pos.position == 12
    assert updated_pos.ave_fill_price == target_ave_price
    assert updated_pos.account == DEFAULT_SIM_ACC
