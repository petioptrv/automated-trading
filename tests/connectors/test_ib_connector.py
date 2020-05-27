from threading import Thread, active_count
from queue import Queue

import pytest


@pytest.fixture
def connector_and_thread():
    pytest.importorskip("ibapi")
    from algotradepy.connectors.ib_connector import IBConnector

    connector = IBConnector()
    connector.managed_connect()

    t = Thread(target=connector.run)
    t.start()

    yield connector, t

    connector.managed_disconnect()


def update_queue(*args, queue: Queue):
    queue.put(item=args)


def test_get_req_id(connector_and_thread):
    connector, t = connector_and_thread

    receiver_queue = Queue()

    connector.subscribe(
        target_fn=connector.nextValidId,
        callback=update_queue,
        callback_kwargs={"queue": receiver_queue},
    )

    connector.reqIds(numIds=1)

    while receiver_queue.empty():
        pass

    req_id = receiver_queue.get()[0]

    assert req_id is not None

    connector.managed_disconnect()

    assert not t.is_alive()


def test_connector_builder_robustness():
    pytest.importorskip("ibapi")
    from algotradepy.connectors.ib_connector import build_and_start_connector

    conn0 = build_and_start_connector()
    conn1 = build_and_start_connector()
    conn2 = build_and_start_connector()

    assert conn0.client_id != conn1.client_id
    assert conn0.client_id != conn2.client_id
    assert conn1.client_id != conn2.client_id

    conn0.managed_disconnect()
    conn1.managed_disconnect()
    conn2.managed_disconnect()
