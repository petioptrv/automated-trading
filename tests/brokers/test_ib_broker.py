import time
from collections import OrderedDict
from typing import Optional

import numpy as np
import pytest

from algotradepy.contracts import AContract, StockContract, Exchange, Currency
from algotradepy.orders import (
    AnOrder,
    LimitOrder,
    OrderAction,
    MarketOrder,
    TrailingStopOrder,
)
from algotradepy.trade import TradeStatus, Trade
from algotradepy.subscribable import Subscribable
from tests.conftest import PROJECT_DIR

AWAIT_TIME_OUT = 10
tests_passed = 0


def increment_tests_passed():
    global tests_passed
    tests_passed += 1


def test_acc_cash():
    pytest.importorskip("ib_insync")
    from algotradepy.brokers.ib_broker import IBBroker

    broker = IBBroker()

    acc_cash = broker.acc_cash

    broker.__del__()

    assert isinstance(acc_cash, float)
    np.testing.assert_allclose(acc_cash, 1e6, atol=1e5)

    increment_tests_passed()


def test_datetime():
    pytest.importorskip("ib_insync")
    from algotradepy.brokers.ib_broker import IBBroker

    from datetime import datetime

    broker = IBBroker()

    broker_dt = broker.datetime
    curr_dt = datetime.now()

    broker.__del__()

    assert broker_dt.date() == curr_dt.date()
    assert broker_dt.hour == curr_dt.hour
    assert broker_dt.min == curr_dt.min
    assert np.isclose(broker_dt.second, curr_dt.second, atol=2)

    increment_tests_passed()


def get_broker(client_id: int):
    pytest.importorskip("ib_insync")
    from algotradepy.connectors.ib_connector import build_and_start_connector
    from algotradepy.brokers.ib_broker import IBBroker

    conn = build_and_start_connector(client_id=client_id)
    broker = IBBroker(ib_connector=conn)

    return broker


@pytest.fixture()
def master_broker():
    pytest.importorskip("ib_insync")
    from algotradepy.connectors.ib_connector import MASTER_CLIENT_ID

    broker = get_broker(client_id=MASTER_CLIENT_ID)

    yield broker

    broker.__del__()


@pytest.fixture()
def non_master_broker():
    pytest.importorskip("ib_insync")
    from algotradepy.connectors.ib_connector import MASTER_CLIENT_ID

    broker = get_broker(client_id=MASTER_CLIENT_ID + 1)

    yield broker

    broker.__del__()


def get_ib_test_broker(client_id: int):
    pytest.importorskip("ib_insync")
    from ib_insync.ib import IB

    class TestBroker(Subscribable, IB):
        def __init__(self):
            Subscribable.__init__(self)
            IB.__init__(self)

    tb = TestBroker()

    ip_address = "127.0.0.1"
    socket_port = 7497

    tb.connect(
        host=ip_address, port=socket_port, clientId=client_id,
    )

    return tb


@pytest.fixture()
def master_ib_test_broker():
    pytest.importorskip("ib_insync")
    from algotradepy.connectors.ib_connector import MASTER_CLIENT_ID

    tb = get_ib_test_broker(client_id=MASTER_CLIENT_ID)

    yield tb

    tb.reqGlobalCancel()
    tb.disconnect()


@pytest.fixture()
def non_master_ib_test_broker():
    pytest.importorskip("ib_insync")
    from algotradepy.connectors.ib_connector import MASTER_CLIENT_ID

    tb = get_ib_test_broker(client_id=MASTER_CLIENT_ID + 1)

    yield tb

    tb.reqGlobalCancel()
    tb.disconnect()


@pytest.fixture()
def ib_stk_contract_spy():
    pytest.importorskip("ib_insync")
    from ib_insync.contract import Stock

    contract = Stock(
        symbol="SPY",
        exchange="SMART",
        currency="USD"
    )

    return contract


@pytest.fixture()
def ib_mkt_buy_order_1():
    pytest.importorskip("ib_insync")
    from ib_insync.order import MarketOrder

    order = MarketOrder(
        action="BUY",
        totalQuantity=1,
    )

    return order


@pytest.fixture()
def ib_mkt_sell_order_1():
    pytest.importorskip("ib_insync")
    from ib_insync.order import MarketOrder

    order = MarketOrder(
        action="SELL",
        totalQuantity=1,
    )

    return order


@pytest.fixture()
def ib_lmt_sell_order_2_1000():
    pytest.importorskip("ib_insync")
    from ib_insync.order import LimitOrder

    order = LimitOrder(
        action="SELL",
        totalQuantity=2,
        lmtPrice=1000,
    )

    return order


@pytest.fixture()
def spy_stock_contract():
    contract = StockContract(symbol="SPY")

    return contract


def test_get_position_non_master_id_raises(
    non_master_broker, spy_stock_contract,
):
    with pytest.raises(AttributeError):
        non_master_broker.get_position(contract=spy_stock_contract)

    increment_tests_passed()


def test_get_position(
    master_broker,
    spy_stock_contract,
    non_master_ib_test_broker,
    ib_stk_contract_spy,
    ib_mkt_buy_order_1,
    ib_mkt_sell_order_1,
):
    from algotradepy.connectors.ib_connector import SERVER_BUFFER_TIME

    initial_position = master_broker.get_position(contract=spy_stock_contract)

    trade = non_master_ib_test_broker.placeOrder(
        contract=ib_stk_contract_spy,
        order=ib_mkt_buy_order_1,
    )

    while trade.isActive() and not trade.isDone():
        non_master_ib_test_broker.sleep(SERVER_BUFFER_TIME)

    spy_position = master_broker.get_position(contract=spy_stock_contract)

    assert spy_position == initial_position + 1

    trade = non_master_ib_test_broker.placeOrder(
        contract=ib_stk_contract_spy,
        order=ib_mkt_sell_order_1,
    )

    while trade.isActive() and not trade.isDone():
        non_master_ib_test_broker.sleep(SERVER_BUFFER_TIME)

    spy_position = master_broker.get_position(contract=spy_stock_contract)

    assert spy_position == initial_position

    increment_tests_passed()


@pytest.mark.parametrize("action", [OrderAction.BUY, OrderAction.SELL])
def test_limit_order(
    non_master_ib_test_broker, master_broker, action,
):
    non_master_ib_test_broker.reqGlobalCancel()

    contract = StockContract(symbol="SPY")
    order = LimitOrder(action=action, quantity=1, limit_price=20)
    trade = Trade(contract=contract, order=order)
    placed, _ = master_broker.place_trade(trade=trade, await_confirm=True)

    assert isinstance(placed, bool)

    increment_tests_passed()


def test_subscribe_to_new_trades_non_master_raises(non_master_broker):
    def dummy_fn(*_, **__):
        pass

    with pytest.raises(AttributeError):
        master_broker.subscribe_to_new_trades(func=dummy_fn)

    increment_tests_passed()


def test_subscribe_to_new_tws_trades(
    master_broker,
    non_master_ib_test_broker,
    ib_stk_contract_spy,
    ib_mkt_buy_order_1,
    ib_lmt_sell_order_2_1000,
):
    already_logged = []
    open_orders = OrderedDict()

    # ---- Helpers ----

    def log_new_trade(trade_: Trade):
        contract_ = trade_.contract
        order_ = trade_.order
        order_id = order_.order_id
        if order_id not in already_logged:
            open_orders[order_id] = {
                "contract": contract_,
                "order": order_,
            }
            already_logged.append(order_id)

    def await_order():
        t0 = t1 = time.time()
        while t1 - t0 <= AWAIT_TIME_OUT and len(open_orders) == 0:
            master_broker.sleep()
            t1 = time.time()

    def get_contract_and_order():
        _, open_order_dict = open_orders.popitem()
        contract_: AContract = open_order_dict["contract"]
        order_: AnOrder = open_order_dict["order"]
        return contract_, order_

    # ----------------

    master_broker.subscribe_to_new_trades(func=log_new_trade)
    non_master_ib_test_broker.placeOrder(
        ib_stk_contract_spy, ib_mkt_buy_order_1,
    )

    await_order()

    assert len(open_orders) == 1

    contract, order = get_contract_and_order()

    assert contract.symbol == "SPY"
    assert isinstance(order, MarketOrder)
    assert order.action == OrderAction.BUY
    assert order.quantity == 1

    non_master_ib_test_broker.placeOrder(
        ib_stk_contract_spy, ib_lmt_sell_order_2_1000,
    )

    await_order()

    assert len(open_orders) == 1

    contract, order = get_contract_and_order()

    assert contract.symbol == "SPY"
    assert isinstance(order, LimitOrder)
    assert order.action == OrderAction.SELL
    assert order.quantity == 2
    assert order.limit_price == 1000

    increment_tests_passed()


def test_subscribe_to_trade_updates_non_master_raises(non_master_broker):
    def dummy_fn(*_, **__):
        pass

    with pytest.raises(AttributeError):
        master_broker.subscribe_to_trade_updates(func=dummy_fn)

    increment_tests_passed()


def test_subscribe_to_tws_trade_updates(
    master_broker,
    non_master_ib_test_broker,
    ib_stk_contract_spy,
    ib_mkt_buy_order_1,
):
    open_orders = OrderedDict()

    def log_order_status(status_: TradeStatus):
        order_id = status_.order_id
        if order_id not in open_orders:
            open_orders[order_id] = status_

    master_broker.subscribe_to_trade_updates(func=log_order_status)
    non_master_ib_test_broker.placeOrder(
        ib_stk_contract_spy, ib_mkt_buy_order_1,
    )

    t0 = t1 = time.time()
    while t1 - t0 <= AWAIT_TIME_OUT and len(open_orders) == 0:
        master_broker.sleep()
        t1 = time.time()

    assert len(open_orders) == 1

    item = open_orders.popitem()
    status: TradeStatus = item[1]

    assert status.filled + status.remaining == 1

    increment_tests_passed()


def request_manual_input(msg):
    from tkinter import messagebox

    messagebox.showwarning(title="Manual Input Request", message=msg)


# def test_order_cancel(master_broker):
#     open_orders = OrderedDict()
#     cancel_received = False
#
#     def log_cancelled_order(status_: TradeStatus):
#         nonlocal cancel_received
#
#         order_id = status_.order_id
#         if status_.state == "Cancelled" and order_id in open_orders:
#             open_orders[order_id] = status_
#
#         cancel_received = True
#
#     order_received = False
#
#     def maybe_cancel_order(contract_: AContract, order_: AnOrder):
#         nonlocal order_received
#
#         if (
#             contract_.symbol == "SPY"
#             and isinstance(order_, LimitOrder)
#             and order_.action == OrderAction.BUY
#             and order_.quantity == 1
#             and order_.limit_price == 10
#         ):
#             open_orders[order_.order_id] = None
#             master_broker.cancel_trade(order_id=order_.order_id)
#             order_received = True
#
#     master_broker.subscribe_to_trade_updates(func=log_cancelled_order)
#     master_broker.subscribe_to_new_trades(func=maybe_cancel_order)
#
#     request_manual_input(
#         msg="Place a SPY limit buy order of 1 share at $10"
#         " in TWS and close this window.\nIf your order doesn't get"
#         " immediately cancelled, this test has failed (close window"
#         " regardless)."
#     )
#
#     t0 = t1 = time.time()
#     while t1 - t0 <= AWAIT_TIME_OUT and (
#         not order_received or not cancel_received
#     ):
#         master_broker.sleep()
#         t1 = time.time()
#
#     assert len(open_orders) == 1
#
#     item = open_orders.popitem()
#     status: TradeStatus = item[1]
#
#     assert status.state == "Cancelled"
#
#     increment_tests_passed()


@pytest.mark.parametrize(
    "exchange,currency,symbol,size",
    [
        (Exchange.NYSE, Currency.USD, "SPY", 1),
        (Exchange.NASDAQ, Currency.USD, "TSLA", 1),
        (Exchange.AMEX, Currency.USD, "TSLA", 1),
        (Exchange.ARCA, Currency.USD, "TSLA", 1),
        (Exchange.TSE, Currency.CAD, "AQN", 1),
        (Exchange.VENTURE, Currency.CAD, "VTI", 1),
        (Exchange.FWB, Currency.EUR, "FME", 1),
        (Exchange.IBIS, Currency.EUR, "SAP", 1),
        (Exchange.VSE, Currency.EUR, "SBO", 1),
        (Exchange.LSE, Currency.GBP, "BRBY", 1),
        (Exchange.BATEUK, Currency.GBP, "GENL", 1),
        (Exchange.ENEXT_BE, Currency.EUR, "BAR", 1),
        (Exchange.SBF, Currency.EUR, "BRE", 1),
        (Exchange.AEB, Currency.EUR, "LQDA", 1),
        (Exchange.SEHK, Currency.HKD, "98", 1000),
        (Exchange.ASX, Currency.AUD, "CML", 1),
        (Exchange.TSEJ, Currency.JPY, "2334", 100),
    ],
)
def test_exchanges_and_currencies(
    exchange, currency, symbol, size, non_master_broker, master_ib_test_broker,
):
    time.sleep(1)
    contract = StockContract(
        symbol=symbol, exchange=exchange, currency=currency,
    )
    order = LimitOrder(action=OrderAction.BUY, quantity=size, limit_price=10)
    trade = Trade(contract=contract, order=order)
    placed, _ = non_master_broker.place_trade(trade=trade, await_confirm=True)

    assert isinstance(placed, bool)

    increment_tests_passed()


def test_trailing_stop_order(master_broker, spy_stock_contract):
    received_contract: Optional[AContract] = None
    received_order: Optional[AnOrder] = None

    def order_receiver(trade_: Trade):
        nonlocal received_order, received_contract

        received_order = trade_.order
        received_contract = trade_.contract

    master_broker.subscribe_to_new_trades(func=order_receiver)

    stop_order = TrailingStopOrder(
        action=OrderAction.BUY,
        quantity=1,
        stop_price=30,
    )
    trade = Trade(contract=spy_stock_contract, order=stop_order)
    _, order_id = master_broker.place_trade(trade=trade, await_confirm=True)

    t0 = t1 = time.time()
    while t1 - t0 <= AWAIT_TIME_OUT and received_contract is None:
        master_broker.sleep()
        t1 = time.time()

    assert received_contract is not None
    assert received_contract.symbol == "SPY"
    assert isinstance(received_order, TrailingStopOrder)
    assert received_order.action == OrderAction.BUY
    assert received_order.stop_price == 30

    master_broker.cancel_trade(trade=trade)


def test_log_all_tests_passed_ts():
    global tests_passed
    assert tests_passed == 27

    ts_f_path = PROJECT_DIR / "test_scripts" / "test_ib_broker_ts.log"

    with open(file=ts_f_path, mode="w") as f:
        ts = str(time.time())
        f.write(ts)
