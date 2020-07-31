import time
from collections import OrderedDict

import numpy as np
import pytest

from algotradepy.contracts import (
    AContract,
    StockContract,
    Exchange,
    Currency,
    ForexContract,
)
from algotradepy.orders import (
    AnOrder,
    LimitOrder,
    OrderAction,
    MarketOrder,
    TrailingStopOrder,
)
from algotradepy.trade import TradeStatus, Trade
from algotradepy.subscribable import Subscribable

AWAIT_TIME_OUT = 10


def test_acc_cash():
    pytest.importorskip("ib_insync")
    from algotradepy.brokers.ib_broker import IBBroker

    broker = IBBroker()

    acc_cash = broker.acc_cash

    broker.__del__()

    assert isinstance(acc_cash, float)
    np.testing.assert_allclose(acc_cash, 1e6, atol=1e5)


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

    contract = Stock(symbol="SPY", exchange="SMART", currency="USD")

    return contract


@pytest.fixture()
def ib_mkt_buy_order_1():
    pytest.importorskip("ib_insync")
    from ib_insync.order import MarketOrder

    order = MarketOrder(action="BUY", totalQuantity=1,)

    return order


@pytest.fixture()
def ib_mkt_sell_order_1():
    pytest.importorskip("ib_insync")
    from ib_insync.order import MarketOrder

    order = MarketOrder(action="SELL", totalQuantity=1,)

    return order


@pytest.fixture()
def ib_lmt_sell_order_2_1000():
    pytest.importorskip("ib_insync")
    from ib_insync.order import LimitOrder

    order = LimitOrder(action="SELL", totalQuantity=2, lmtPrice=1000,)

    return order


@pytest.fixture()
def spy_stock_contract():
    contract = StockContract(symbol="SPY")

    return contract


def test_subscribe_to_new_trades_non_master_raises(non_master_broker):
    def dummy_fn(*_, **__):
        pass

    with pytest.raises(AttributeError):
        master_broker.subscribe_to_new_trades(func=dummy_fn)


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


def test_subscribe_to_trade_updates_non_master_raises(non_master_broker):
    def dummy_fn(*_, **__):
        pass

    with pytest.raises(AttributeError):
        master_broker.subscribe_to_trade_updates(func=dummy_fn)


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


def request_manual_input(msg):
    from tkinter import messagebox

    messagebox.showwarning(title="Manual Input Request", message=msg)


def test_get_position_non_master_id_raises(
    non_master_broker, spy_stock_contract,
):
    with pytest.raises(AttributeError):
        non_master_broker.get_position(contract=spy_stock_contract)


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
        contract=ib_stk_contract_spy, order=ib_mkt_buy_order_1,
    )

    while trade.isActive() and not trade.isDone():
        non_master_ib_test_broker.sleep(SERVER_BUFFER_TIME)

    spy_position = master_broker.get_position(contract=spy_stock_contract)

    assert spy_position == initial_position + 1

    trade = non_master_ib_test_broker.placeOrder(
        contract=ib_stk_contract_spy, order=ib_mkt_sell_order_1,
    )

    while trade.isActive() and not trade.isDone():
        non_master_ib_test_broker.sleep(SERVER_BUFFER_TIME)

    spy_position = master_broker.get_position(contract=spy_stock_contract)

    assert spy_position == initial_position


def test_place_limit_order(master_ib_test_broker, non_master_broker):
    master_ib_test_broker.reqGlobalCancel()
    ib_trade = None

    def trade_receiver(trade_):
        nonlocal ib_trade
        ib_trade = trade_

    master_ib_test_broker.openOrderEvent += trade_receiver

    contract = StockContract(symbol="SPY")
    order = LimitOrder(action=OrderAction.BUY, quantity=1, limit_price=20)
    trade = Trade(contract=contract, order=order)
    placed, _ = non_master_broker.place_trade(trade=trade, await_confirm=True)

    assert isinstance(placed, bool)

    t0 = time.time()
    while ib_trade is None and time.time() - t0 <= AWAIT_TIME_OUT:
        non_master_broker.sleep()

    assert ib_trade.contract.symbol == "SPY"
    assert ib_trade.order.orderType == "LMT"
    assert ib_trade.order.totalQuantity == 1
    assert ib_trade.order.action == "BUY"
    assert ib_trade.order.lmtPrice == 20


def test_receive_limit_order(non_master_ib_test_broker, master_broker):
    from ib_insync.order import LimitOrder as IBLimitOrder
    from ib_insync.contract import Stock as IBStock

    trade: Trade = None

    def trade_receiver(trade_):
        nonlocal trade
        trade = trade_

    master_broker.subscribe_to_new_trades(func=trade_receiver)

    contract = IBStock(symbol="SPY", exchange="SMART", currency="USD")
    order = IBLimitOrder(action="BUY", totalQuantity=1, lmtPrice=10)
    non_master_ib_test_broker.placeOrder(contract=contract, order=order)

    t0 = time.time()
    while trade is None and time.time() - t0 <= AWAIT_TIME_OUT:
        master_broker.sleep()

    assert trade.contract.symbol == "SPY"
    assert isinstance(trade.order, LimitOrder)
    assert trade.order.quantity == 1
    assert trade.order.action == OrderAction.BUY
    assert trade.order.limit_price == 10


@pytest.mark.parametrize("aux_price,trailing_percent", [(5, None), (None, 5)])
def test_place_trailing_stop_order(
    aux_price, trailing_percent, master_ib_test_broker, non_master_broker,
):
    from ib_insync.util import UNSET_DOUBLE

    master_ib_test_broker.reqGlobalCancel()
    ib_trade = None

    def trade_receiver(trade_):
        nonlocal ib_trade
        ib_trade = trade_

    master_ib_test_broker.openOrderEvent += trade_receiver

    contract = StockContract(symbol="SPY")
    order = TrailingStopOrder(
        action=OrderAction.BUY,
        quantity=1,
        trail_stop_price=10,
        aux_price=aux_price,
        trail_percent=trailing_percent,
    )
    trade = Trade(contract=contract, order=order)
    placed, _ = non_master_broker.place_trade(trade=trade, await_confirm=True)

    assert isinstance(placed, bool)

    t0 = time.time()
    while ib_trade is None and time.time() - t0 <= AWAIT_TIME_OUT:
        non_master_broker.sleep()

    assert ib_trade.contract.symbol == "SPY"
    assert ib_trade.order.orderType == "TRAIL"
    assert ib_trade.order.totalQuantity == 1
    assert ib_trade.order.action == "BUY"
    assert ib_trade.order.trailStopPrice == 10
    if aux_price is not None:
        assert ib_trade.order.auxPrice == aux_price
    else:
        assert ib_trade.order.auxPrice == UNSET_DOUBLE
    if trailing_percent is not None:
        assert ib_trade.order.trailingPercent == trailing_percent
    else:
        assert ib_trade.order.trailingPercent == UNSET_DOUBLE


@pytest.mark.parametrize("aux_price,trailing_percent", [(5, None), (None, 5)])
def test_receive_trailing_stop_order(
    aux_price, trailing_percent, non_master_ib_test_broker, master_broker,
):
    from ib_insync.util import UNSET_DOUBLE
    from ib_insync.order import Order as IBorder
    from ib_insync.contract import Stock as IBStock

    trade: Trade = None

    def trade_receiver(trade_):
        nonlocal trade
        trade = trade_

    master_broker.subscribe_to_new_trades(func=trade_receiver)

    contract = IBStock(symbol="SPY", exchange="SMART", currency="USD")
    order = IBorder(
        orderType="TRAIL",
        action="BUY",
        totalQuantity=1,
        trailStopPrice=10,
        auxPrice=aux_price or UNSET_DOUBLE,
        trailingPercent=trailing_percent or UNSET_DOUBLE,
    )
    non_master_ib_test_broker.placeOrder(contract=contract, order=order)

    t0 = time.time()
    while trade is None and time.time() - t0 <= AWAIT_TIME_OUT:
        master_broker.sleep()

    assert trade.contract.symbol == "SPY"
    assert isinstance(trade.order, TrailingStopOrder)
    assert trade.order.quantity == 1
    assert trade.order.action == OrderAction.BUY
    assert trade.order.trail_stop_price == 10
    assert trade.order.aux_price == aux_price
    assert trade.order.trail_percent == trailing_percent


def test_place_forex_order(master_ib_test_broker, non_master_broker):
    master_ib_test_broker.reqGlobalCancel()
    ib_trade = None

    def trade_receiver(trade_):
        nonlocal ib_trade
        ib_trade = trade_

    master_ib_test_broker.openOrderEvent += trade_receiver

    contract = ForexContract(symbol="EUR", currency=Currency.USD)
    order = LimitOrder(action=OrderAction.BUY, quantity=20000, limit_price=1)
    trade = Trade(contract=contract, order=order)
    placed, _ = non_master_broker.place_trade(trade=trade, await_confirm=True)

    assert isinstance(placed, bool)

    t0 = time.time()
    while ib_trade is None and time.time() - t0 <= AWAIT_TIME_OUT:
        non_master_broker.sleep()

    assert ib_trade.contract.symbol == "EUR"
    assert ib_trade.contract.secType == "CASH"
    assert ib_trade.order.orderType == "LMT"
    assert ib_trade.order.totalQuantity == 20000
    assert ib_trade.order.action == "BUY"
    assert ib_trade.order.lmtPrice == 1


def test_receive_forex_order(non_master_ib_test_broker, master_broker):
    from ib_insync.order import LimitOrder as IBLimitOrder
    from ib_insync.contract import Forex as IBForex

    trade: Trade = None

    def trade_receiver(trade_):
        nonlocal trade
        trade = trade_

    master_broker.subscribe_to_new_trades(func=trade_receiver)

    contract = IBForex(pair="EURUSD")
    order = IBLimitOrder(action="BUY", totalQuantity=20000, lmtPrice=1)
    non_master_ib_test_broker.placeOrder(contract=contract, order=order)

    t0 = time.time()
    while trade is None and time.time() - t0 <= AWAIT_TIME_OUT:
        master_broker.sleep()

    assert trade.contract.symbol == "EUR"
    assert isinstance(trade.contract, ForexContract)
    assert trade.order.quantity == 20000
    assert trade.order.action == OrderAction.BUY
    assert trade.order.limit_price == 1


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
