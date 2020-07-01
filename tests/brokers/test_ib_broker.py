import time
from collections import OrderedDict

import numpy as np
import pytest
from threading import Thread

from algotradepy.contracts import AContract, StockContract, Exchange, Currency
from algotradepy.orders import (
    AnOrder,
    OrderStatus,
    LimitOrder,
    OrderAction,
    MarketOrder,
)
from algotradepy.subscribable import Subscribable
from tests.conftest import PROJECT_DIR

AWAIT_TIME_OUT = 10
tests_passed = 0


def increment_tests_passed():
    global tests_passed
    tests_passed += 1


def test_acc_cash():
    pytest.importorskip("ibapi")
    from algotradepy.brokers.ib_broker import IBBroker

    broker = IBBroker()

    acc_cash = broker.acc_cash

    broker.__del__()

    assert isinstance(acc_cash, float)
    assert acc_cash > 0

    increment_tests_passed()


def test_datetime():
    pytest.importorskip("ibapi")
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
    pytest.importorskip("ibapi")
    from algotradepy.connectors.ib_connector import build_and_start_connector
    from algotradepy.brokers.ib_broker import IBBroker

    conn = build_and_start_connector(client_id=client_id)
    broker = IBBroker(ib_connector=conn)

    return broker


@pytest.fixture()
def master_broker():
    pytest.importorskip("ibapi")
    from algotradepy.connectors.ib_connector import MASTER_CLIENT_ID

    broker = get_broker(client_id=MASTER_CLIENT_ID)

    yield broker

    broker.__del__()


@pytest.fixture()
def non_master_broker():
    pytest.importorskip("ibapi")
    from algotradepy.connectors.ib_connector import MASTER_CLIENT_ID

    broker = get_broker(client_id=MASTER_CLIENT_ID + 1)

    yield broker

    broker.__del__()


def get_ib_test_broker(client_id: int):
    pytest.importorskip("ibapi")

    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from algotradepy.connectors.ib_connector import SERVER_BUFFER_TIME

    class TestBroker(Subscribable, EWrapper, EClient):
        def __init__(self):
            Subscribable.__init__(self)
            EWrapper.__init__(self)
            EClient.__init__(self, wrapper=self)

            self._valid_id = None
            self.conn_ack = False

        def nextValidId(self, orderId: int):
            super().nextValidId(orderId=orderId)
            self._valid_id = orderId

        def connectAck(self):
            super().connectAck()
            self.conn_ack = True

        def get_increment_valid_id(self) -> int:
            valid_id = self._valid_id
            self._valid_id += 1
            return valid_id

    tb = TestBroker()

    ip_address = "127.0.0.1"
    socket_port = 7497

    tb.connect(
        host=ip_address, port=socket_port, clientId=client_id,
    )

    run_thread = Thread(target=tb.run)
    run_thread.start()

    time.sleep(SERVER_BUFFER_TIME)

    while not tb.conn_ack:
        time.sleep(SERVER_BUFFER_TIME)

    while tb._valid_id is None:
        tb.reqIds(numIds=1)
        time.sleep(SERVER_BUFFER_TIME)

    return tb


@pytest.fixture()
def master_ib_test_broker():
    pytest.importorskip("ibapi")
    from algotradepy.connectors.ib_connector import MASTER_CLIENT_ID

    tb = get_ib_test_broker(client_id=MASTER_CLIENT_ID)

    yield tb

    tb.reqGlobalCancel()
    tb.disconnect()


@pytest.fixture()
def non_master_ib_test_broker():
    pytest.importorskip("ibapi")
    from algotradepy.connectors.ib_connector import MASTER_CLIENT_ID

    tb = get_ib_test_broker(client_id=MASTER_CLIENT_ID + 1)

    yield tb

    tb.reqGlobalCancel()
    tb.disconnect()


@pytest.fixture()
def ib_stk_contract_spy():
    pytest.importorskip("ibapi")
    from ibapi.contract import Contract

    contract = Contract()
    contract.symbol = "SPY"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    return contract


@pytest.fixture()
def ib_mkt_buy_order_1():
    pytest.importorskip("ibapi")
    from ibapi.order import Order

    order = Order()
    order.action = "BUY"
    order.orderType = "MKT"
    order.totalQuantity = 1

    return order


@pytest.fixture()
def ib_mkt_sell_order_1():
    pytest.importorskip("ibapi")
    from ibapi.order import Order

    order = Order()
    order.action = "SELL"
    order.orderType = "MKT"
    order.totalQuantity = 1

    return order


@pytest.fixture()
def ib_lmt_sell_order_2_1000():
    pytest.importorskip("ibapi")
    from ibapi.order import Order

    order = Order()
    order.action = "SELL"
    order.orderType = "LMT"
    order.totalQuantity = 2
    order.lmtPrice = 1000

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
    order_filled = False
    target_order_id = non_master_ib_test_broker._valid_id

    def order_status_custom(order_id, status, *args):
        nonlocal order_filled, target_order_id
        if order_id == target_order_id and status == "Filled":
            order_filled = True

    non_master_ib_test_broker.subscribe(
        target_fn=non_master_ib_test_broker.orderStatus,
        callback=order_status_custom,
    )

    non_master_ib_test_broker.placeOrder(
        orderId=target_order_id,
        contract=ib_stk_contract_spy,
        order=ib_mkt_buy_order_1,
    )

    while not order_filled:
        time.sleep(SERVER_BUFFER_TIME)

    spy_position = master_broker.get_position(contract=spy_stock_contract)

    assert spy_position == initial_position + 1

    ib_mkt_sell_order_1.totalQuantity = spy_position
    target_order_id = target_order_id + 1
    non_master_ib_test_broker.placeOrder(
        orderId=target_order_id,
        contract=ib_stk_contract_spy,
        order=ib_mkt_sell_order_1,
    )
    time.sleep(SERVER_BUFFER_TIME * 2)

    spy_position = master_broker.get_position(contract=spy_stock_contract)

    assert spy_position == 0

    increment_tests_passed()


@pytest.mark.parametrize("action", [OrderAction.BUY, OrderAction.SELL])
def test_limit_order(
    non_master_ib_test_broker, master_broker, action,
):

    non_master_ib_test_broker.reqGlobalCancel()

    contract = StockContract(symbol="SPY")
    order = LimitOrder(action=action, quantity=1, limit_price=20)
    placed, _ = master_broker.place_order(
        contract=contract, order=order, await_confirm=True
    )

    assert isinstance(placed, bool)

    increment_tests_passed()


def test_subscribe_to_new_trades_non_master_raises(non_master_broker):
    def dummy_fn(*_, **__):
        pass

    with pytest.raises(AttributeError):
        master_broker.subscribe_to_new_trades(func=dummy_fn)

    increment_tests_passed()


@pytest.fixture()
def order_dict_and_update_fn():
    open_orders = OrderedDict()

    def log_new_order(contract_: AContract, order_: AnOrder):
        order_id = order_.order_id
        if order_id not in open_orders:
            open_orders[order_id] = {
                "contract": contract_,
                "order": order_,
            }

    return open_orders, log_new_order


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

    def log_new_order(contract_: AContract, order_: AnOrder):
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
            time.sleep(1)
            t1 = time.time()

    def get_contract_and_order():
        _, open_order_dict = open_orders.popitem()
        contract_: AContract = open_order_dict["contract"]
        order_: AnOrder = open_order_dict["order"]
        return contract_, order_

    # ----------------

    master_broker.subscribe_to_new_trades(func=log_new_order)
    valid_id = non_master_ib_test_broker.get_increment_valid_id()
    non_master_ib_test_broker.placeOrder(
        valid_id, ib_stk_contract_spy, ib_mkt_buy_order_1,
    )

    await_order()

    assert len(open_orders) == 1

    contract, order = get_contract_and_order()

    assert contract.symbol == "SPY"
    assert isinstance(order, MarketOrder)
    assert order.action == OrderAction.BUY
    assert order.quantity == 1

    valid_id = non_master_ib_test_broker.get_increment_valid_id()
    non_master_ib_test_broker.placeOrder(
        valid_id, ib_stk_contract_spy, ib_lmt_sell_order_2_1000,
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

    def log_order_status(status_: OrderStatus):
        order_id = status_.order_id
        if order_id not in open_orders:
            open_orders[order_id] = status_

    master_broker.subscribe_to_trade_updates(func=log_order_status)
    valid_id = non_master_ib_test_broker.get_increment_valid_id()
    non_master_ib_test_broker.placeOrder(
        valid_id, ib_stk_contract_spy, ib_mkt_buy_order_1,
    )

    t0 = t1 = time.time()
    while t1 - t0 <= AWAIT_TIME_OUT and len(open_orders) == 0:
        time.sleep(1)
        t1 = time.time()

    assert len(open_orders) == 1

    item = open_orders.popitem()
    status: OrderStatus = item[1]

    assert status.filled + status.remaining == 1

    increment_tests_passed()


def request_manual_input(msg):
    from tkinter import messagebox

    messagebox.showwarning(title="Manual Input Request", message=msg)


def test_order_cancel(master_broker):
    open_orders = OrderedDict()
    cancel_received = False

    def log_cancelled_order(status_: OrderStatus):
        nonlocal cancel_received

        order_id = status_.order_id
        if status_.state == "Cancelled" and order_id in open_orders:
            open_orders[order_id] = status_

        cancel_received = True

    order_received = False

    def maybe_cancel_order(contract_: AContract, order_: AnOrder):
        nonlocal order_received

        if (
            contract_.symbol == "SPY"
            and isinstance(order_, LimitOrder)
            and order_.action == OrderAction.BUY
            and order_.quantity == 1
            and order_.limit_price == 10
        ):
            open_orders[order_.order_id] = None
            master_broker.cancel_order(order_id=order_.order_id)
            order_received = True

    master_broker.subscribe_to_trade_updates(func=log_cancelled_order)
    master_broker.subscribe_to_new_trades(func=maybe_cancel_order)

    request_manual_input(
        msg="Place a SPY limit buy order of 1 share at $10"
        " in TWS and close this window.\nIf your order doesn't get"
        " immediately cancelled, this test has failed (close window"
        " regardless)."
    )

    t0 = t1 = time.time()
    while t1 - t0 <= AWAIT_TIME_OUT and (
        not order_received or not cancel_received
    ):
        time.sleep(1)
        t1 = time.time()

    assert len(open_orders) == 1

    item = open_orders.popitem()
    status: OrderStatus = item[1]

    assert status.state == "Cancelled"

    increment_tests_passed()


@pytest.mark.parametrize(
    "exchange,currency,symbol,size",
    [
        (Exchange.NYSE, Currency.USD, "SPY", 1),
        (Exchange.NASDAQ, Currency.USD, "TSLA", 1),
        (Exchange.TSE, Currency.CAD, "AQN", 1),
        (Exchange.VENTURE, Currency.CAD, "VTI", 1),
        (Exchange.FWB, Currency.EUR, "FME", 1),
        (Exchange.IBIS, Currency.EUR, "SAP", 1),
        (Exchange.VSE, Currency.EUR, "SBO", 1),
        (Exchange.LSE, Currency.GBP, "BRBY", 1),
        (Exchange.BATEUK, Currency.GBP, "GENL", 1),
        (Exchange.SEHK, Currency.HKD, "98", 1000),
        (Exchange.ASX, Currency.AUD, "CML", 1),
        (Exchange.TSEJ, Currency.JPY, "2334", 100),
    ],
)
def test_exchanges_and_currencies(
    exchange, currency, symbol, size, non_master_broker, master_ib_test_broker,
):
    contract = StockContract(
        symbol=symbol, exchange=exchange, currency=currency,
    )
    order = LimitOrder(action=OrderAction.BUY, quantity=size, limit_price=10)
    placed, _ = non_master_broker.place_order(
        contract=contract, order=order, await_confirm=True
    )

    assert isinstance(placed, bool)

    increment_tests_passed()


def test_log_all_tests_passed_ts():
    global tests_passed
    assert tests_passed == 23

    ts_f_path = PROJECT_DIR / "test_scripts" / "test_ib_broker_ts.log"

    with open(file=ts_f_path, mode="w") as f:
        ts = str(time.time())
        f.write(ts)
