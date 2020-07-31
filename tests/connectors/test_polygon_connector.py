import threading
import time
from datetime import date, datetime

import pytest

from tests.conftest import can_test_polygon


@pytest.mark.skipif(not can_test_polygon(), reason="Polygon not available.")
def test_rest_get_exchanges(polygon_api_token):
    from algotradepy.connectors.polygon_connector import PolygonRESTConnector

    conn = PolygonRESTConnector(api_token=polygon_api_token)
    exchanges = conn.get_exchanges()

    assert len(exchanges) == 34


@pytest.mark.skipif(not can_test_polygon(), reason="Polygon not available.")
def test_rest_download_trades_data(polygon_api_token):
    from algotradepy.connectors.polygon_connector import PolygonRESTConnector

    conn = PolygonRESTConnector(api_token=polygon_api_token)
    target_date = date(2020, 7, 27)
    data = conn.download_trades_data(symbol="TSLA", request_date=target_date)

    first_date = datetime.fromtimestamp(data["y"].iloc[0] / 1e9).date()
    last_date = datetime.fromtimestamp(data["y"].iloc[-1] / 1e9).date()

    assert first_date == target_date
    assert last_date == target_date


@pytest.mark.skipif(not can_test_polygon(), reason="Polygon not available.")
def test_ws_connect(polygon_api_token):
    from algotradepy.connectors.polygon_connector import (
        PolygonWebSocketConnector,
    )

    conn = PolygonWebSocketConnector(api_token=polygon_api_token)
    conn.connect()
    conn.disconnect()


@pytest.fixture()
def ws_conn(polygon_api_token):
    from algotradepy.connectors.polygon_connector import (
        PolygonWebSocketConnector,
    )

    conn = PolygonWebSocketConnector(api_token=polygon_api_token)
    conn.connect()

    yield conn

    conn.disconnect()


@pytest.mark.skipif(not can_test_polygon(), reason="Polygon not available.")
def test_ws_sub_to_trade_single(ws_conn):
    event = None
    received = threading.Event()

    def event_receiver(e):
        nonlocal event
        nonlocal received

        if event is None:
            event = e
            received.set()

    ws_conn.subscribe_to_trade_event(func=event_receiver)
    ws_conn.request_trade_data(symbol="TSLA")

    received.wait(2)

    assert isinstance(event, dict)
    assert "ev" in event
    assert event["ev"] == "T"
    assert event["sym"] == "TSLA"


@pytest.mark.skipif(not can_test_polygon(), reason="Polygon not available.")
def test_ws_sub_to_trade_multiple(ws_conn):
    tsla_event = None
    tsla_received = threading.Event()
    spy_event = None
    spy_received = threading.Event()

    def event_receiver(e):
        nonlocal tsla_event
        nonlocal tsla_received
        nonlocal spy_event
        nonlocal spy_received

        if e["sym"] == "TSLA" and tsla_event is None:
            tsla_event = e
            tsla_received.set()
        elif e["sym"] == "SPY" and spy_event is None:
            spy_event = e
            spy_received.set()

    ws_conn.subscribe_to_trade_event(func=event_receiver)
    ws_conn.request_trade_data(symbol="TSLA")
    ws_conn.request_trade_data(symbol="SPY")

    tsla_received.wait(2)
    spy_received.wait(2)

    assert tsla_event["sym"] == "TSLA"
    assert spy_event["sym"] == "SPY"


@pytest.mark.skipif(not can_test_polygon(), reason="Polygon not available.")
def test_ws_unsub_to_trade(ws_conn):
    event = None
    received = threading.Event()

    def event_receiver(e):
        nonlocal event
        nonlocal received

        event = e
        if not received.is_set():
            received.set()

    ws_conn.subscribe_to_trade_event(func=event_receiver)
    ws_conn.request_trade_data(symbol="TSLA")

    received.wait(1)

    t = event["t"]

    time.sleep(2)

    assert event["t"] != t  # updating

    ws_conn.unsubscribe_from_trade_event(func=event_receiver)
    t = event["t"]

    time.sleep(2)

    assert event["t"] == t  # no longer updating


@pytest.mark.skipif(not can_test_polygon(), reason="Polygon not available.")
def test_ws_cancel_trade(ws_conn):
    event = None
    received = threading.Event()

    def event_receiver(e):
        nonlocal event
        nonlocal received

        event = e
        if not received.is_set():
            received.set()

    ws_conn.subscribe_to_trade_event(func=event_receiver)
    ws_conn.request_trade_data(symbol="TSLA")

    received.wait(2)

    t = event["t"]

    time.sleep(2)

    assert event["t"] != t  # updating

    ws_conn.cancel_trade_data(symbol="TSLA")
    time.sleep(1)
    event = None

    time.sleep(2)

    assert event is None  # no longer updating
