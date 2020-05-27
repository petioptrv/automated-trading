import numpy as np
import pytest


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


def test_get_zero_position():
    pytest.importorskip("ibapi")
    from algotradepy.connectors.ib_connector import (
        build_and_start_connector,
        MASTER_CLIENT_ID,
    )
    from algotradepy.brokers.ib_broker import IBBroker

    conn = build_and_start_connector(client_id=MASTER_CLIENT_ID)
    broker = IBBroker(ib_connector=conn)

    spy_position = broker.get_position(symbol="SPY")

    broker.__del__()

    assert spy_position == 0
