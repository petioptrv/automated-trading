import time
from collections import OrderedDict

import numpy as np
import pytest
from threading import Thread

from algotradepy.connectors.ib_connector import SERVER_BUFFER_TIME
from algotradepy.contracts import AContract, STKContract
from algotradepy.orders import AnOrder, OrderStatus, LimitOrder, OrderAction
from algotradepy.subscribable import Subscribable


def test_acc_cash():
    pytest.importorskip("ibapi")
    from algotradepy.brokers.ib_broker import IBBroker

    broker = IBBroker()

    acc_cash = broker.acc_cash

    broker.__del__()

    assert isinstance(acc_cash, float)
    assert acc_cash > 0


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


def test_get_position_non_master_id_raises():
    pytest.importorskip("ibapi")
    from algotradepy.connectors.ib_connector import (
        build_and_start_connector,
        MASTER_CLIENT_ID,
    )
    from algotradepy.brokers.ib_broker import IBBroker

    conn = build_and_start_connector(client_id=MASTER_CLIENT_ID + 1)
    broker = IBBroker(ib_connector=conn)

    with pytest.raises(AttributeError):
        broker.get_position(symbol="SPY")

    conn.managed_disconnect()


@pytest.fixture
def broker():
    pytest.importorskip("ibapi")
    from algotradepy.connectors.ib_connector import (
        build_and_start_connector,
        MASTER_CLIENT_ID,
    )
    from algotradepy.brokers.ib_broker import IBBroker

    conn = build_and_start_connector(client_id=MASTER_CLIENT_ID)
    broker = IBBroker(ib_connector=conn)

    yield broker

    broker.__del__()


@pytest.fixture
def ib_test_broker():
    pytest.importorskip("ibapi")

    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper

    class TestBroker(Subscribable, EWrapper, EClient):
        def __init__(self):
            Subscribable.__init__(self)
            EWrapper.__init__(self)
            EClient.__init__(self, wrapper=self)

            self.valid_id = None
            self.conn_ack = False

        def nextValidId(self, orderId: int):
            super().nextValidId(orderId=orderId)
            self.valid_id = orderId

        def connectAck(self):
            super().connectAck()
            self.conn_ack = True

    tb = TestBroker()

    ip_address = "127.0.0.1"
    socket_port = 7497
    client_id = 2

    tb.connect(
        host=ip_address, port=socket_port, clientId=client_id,
    )

    run_thread = Thread(target=tb.run)
    run_thread.start()

    time.sleep(SERVER_BUFFER_TIME)

    while not tb.conn_ack:
        time.sleep(SERVER_BUFFER_TIME)

    while tb.valid_id is None:
        tb.reqIds(numIds=1)
        time.sleep(SERVER_BUFFER_TIME)

    yield tb

    tb.reqGlobalCancel()
    tb.disconnect()


@pytest.fixture
def ib_stk_contract():
    pytest.importorskip("ibapi")
    from ibapi.contract import Contract

    contract = Contract()
    contract.symbol = "SPY"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    return contract


@pytest.fixture
def ib_mkt_buy_order():
    pytest.importorskip("ibapi")
    from ibapi.order import Order

    order = Order()
    order.action = "BUY"
    order.orderType = "MKT"
    order.totalQuantity = 1

    return order


@pytest.fixture
def ib_mkt_sell_order():
    pytest.importorskip("ibapi")
    from ibapi.order import Order

    order = Order()
    order.action = "SELL"
    order.orderType = "MKT"
    order.totalQuantity = 1

    return order


def test_get_position(
    broker,
    ib_test_broker,
    ib_stk_contract,
    ib_mkt_buy_order,
    ib_mkt_sell_order,
):
    initial_position = broker.get_position(symbol="SPY")
    order_filled = False
    target_order_id = ib_test_broker.valid_id

    def order_status_custom(order_id, status, *args):
        nonlocal order_filled, target_order_id
        if order_id == target_order_id and status == "Filled":
            order_filled = True

    ib_test_broker.subscribe(
        target_fn=ib_test_broker.orderStatus, callback=order_status_custom,
    )

    ib_test_broker.placeOrder(
        orderId=target_order_id,
        contract=ib_stk_contract,
        order=ib_mkt_buy_order,
    )

    while not order_filled:
        time.sleep(SERVER_BUFFER_TIME)

    spy_position = broker.get_position(symbol="SPY")

    assert spy_position == initial_position + 1

    order_filled = False
    target_order_id = target_order_id + 1
    ib_test_broker.placeOrder(
        orderId=target_order_id,
        contract=ib_stk_contract,
        order=ib_mkt_sell_order,
    )

    while not order_filled:
        time.sleep(SERVER_BUFFER_TIME)

    spy_position = broker.get_position(symbol="SPY")

    assert spy_position == initial_position


@pytest.mark.parametrize("action", [OrderAction.BUY, OrderAction.SELL])
def test_limit_order(ib_test_broker, broker, action):
    ib_test_broker.reqGlobalCancel()

    contract = STKContract(symbol="SPY")
    order = LimitOrder(action=action, quantity=1, limit_price=20)
    placed = broker.place_order(contract=contract, order=order)

    assert isinstance(placed, bool)

    ib_test_broker.reqGlobalCancel()


def test_subscribe_to_new_orders(
    broker,
    # test_broker,
    # stk_contract,
    # mkt_buy_order,
):
    open_orders = OrderedDict()

    def log_new_order(contract_: AContract, order_: AnOrder):
        order_id = order_.order_id
        if order_id not in open_orders:
            open_orders[order_id] = {
                "contract": contract_,
                "order": order_,
            }

    broker.subscribe_to_new_orders(func=log_new_order)

    # test_broker.placeOrder(
    #     orderId=test_broker.valid_id,
    #     contract=stk_contract,
    #     order=mkt_buy_order,
    # )

    print("You have 20s to place a SPY market buy order of 1 share")
    time.sleep(20)

    assert len(open_orders) == 1


def test_subscribe_to_order_updates(
    broker, ib_test_broker, ib_stk_contract, ib_mkt_buy_order,
):
    open_orders = OrderedDict()

    def log_new_order(status_: OrderStatus):
        order_id = status_.order_id
        if order_id not in open_orders:
            open_orders[order_id] = status_

    broker.subscribe_to_order_updates(func=log_new_order)

    ib_test_broker.placeOrder(
        orderId=ib_test_broker.valid_id,
        contract=ib_stk_contract,
        order=ib_mkt_buy_order,
    )

    time.sleep(1)

    assert len(open_orders) == 1
