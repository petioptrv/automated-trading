import time

import pytest
import numpy as np

from tests.conftest import PROJECT_DIR


def test_connection():
    pytest.importorskip("ib_insync")
    from algotradepy.connectors.ib_connector import build_and_start_connector

    connector = build_and_start_connector()

    assert connector.isConnected()


def test_connector_builder_robustness():
    pytest.importorskip("ib_insync")
    from algotradepy.connectors.ib_connector import build_and_start_connector

    conn0 = build_and_start_connector()
    conn1 = build_and_start_connector()
    conn2 = build_and_start_connector()

    assert conn0.isConnected()
    assert conn0.isConnected()
    assert conn1.isConnected()

    conn0.disconnect()
    conn1.disconnect()
    conn2.disconnect()


def test_ib_insync_events():
    pytest.importorskip("ib_insync")
    from algotradepy.connectors.ib_connector import build_and_start_connector

    event_received = False

    def event_callback():
        nonlocal event_received

        event_received = True

    conn = build_and_start_connector()
    conn.disconnectedEvent += event_callback
    conn.disconnect()

    assert event_received


@pytest.fixture()
def connector():
    pytest.importorskip("ib_insync")
    from algotradepy.connectors.ib_connector import build_and_start_connector

    conn = build_and_start_connector()

    yield conn

    conn.disconnect()


def test_get_position(connector):
    positions = connector.positions()

    spy_pos = 0
    for position in positions:
        if position.contract.symbol == "SPY":
            spy_pos += position.position

    assert spy_pos == 0  # fix to not rely on absolute value


def test_acc_summary(connector):
    acc_summary = connector.accountSummary()

    acc_values = [s for s in acc_summary if s.tag == "TotalCashValue"]

    total_val = 0
    for v in acc_values:
        total_val += float(v.value)

    np.testing.assert_allclose(total_val, 1e6, atol=1e5)
