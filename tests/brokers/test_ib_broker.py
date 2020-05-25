import numpy as np
import pytest

from algotradepy.brokers.ib_broker import IBBroker


@pytest.fixture
def broker() -> IBBroker:
    broker = IBBroker()
    return broker


def test_acc_cash(broker):
    acc_cash = broker.acc_cash

    assert isinstance(acc_cash, float)
    assert acc_cash > 0


def test_datetime(broker):
    from datetime import datetime

    broker_dt = broker.datetime
    curr_dt = datetime.now()

    assert broker_dt.date() == curr_dt.date()
    assert broker_dt.hour == curr_dt.hour
    assert broker_dt.min == curr_dt.min
    assert np.isclose(broker_dt.second, curr_dt.second, atol=1)
