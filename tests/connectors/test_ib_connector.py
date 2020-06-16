import time
from threading import Thread, active_count
from queue import Queue

import pytest

from tests.conftest import PROJECT_DIR

tests_ran = 0


def increment_tests_ran():
    global tests_ran
    tests_ran += 1


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
    increment_tests_ran()

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
    time.sleep(1)

    assert not t.is_alive()


def test_connector_builder_robustness():
    pytest.importorskip("ibapi")
    from algotradepy.connectors.ib_connector import build_and_start_connector

    increment_tests_ran()

    conn0 = build_and_start_connector()
    conn1 = build_and_start_connector()
    conn2 = build_and_start_connector()

    assert conn0.client_id != conn1.client_id
    assert conn0.client_id != conn2.client_id
    assert conn1.client_id != conn2.client_id

    conn0.managed_disconnect()
    conn1.managed_disconnect()
    conn2.managed_disconnect()


def test_log_all_tests_run_ts():
    global tests_ran
    assert tests_ran == 2

    ts_f_path = PROJECT_DIR / "test_scripts" / "test_ib_connector_ts.log"

    with open(file=ts_f_path, mode="w") as f:
        ts = str(time.time())
        f.write(ts)
