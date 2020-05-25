from threading import Thread
from queue import Queue

import pytest


@pytest.fixture
def connector():
    pytest.importorskip("ibapi")
    from algotradepy.connectors.ib_connector import IBConnector

    connector = IBConnector()

    t = Thread(target=connector.run)
    t.start()

    yield connector

    connector.stop()


def update_queue(queue: Queue, *args):
    queue.put(item=args)


def test_get_req_id(connector):
    receiver_queue = Queue()

    connector.subscribe(
        target_fn=connector.nextValidId,
        callback=update_queue,
        callback_kwargs=(receiver_queue,),
    )

    connector.reqIds(numIds=1)

    while receiver_queue.empty():
        pass

    req_id = receiver_queue.get()[0]

    assert req_id is not None
