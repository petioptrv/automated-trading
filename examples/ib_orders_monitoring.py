from algotradepy.brokers.ib_broker import IBBroker
from algotradepy.connectors.ib_connector import build_and_start_connector


def monitor():
    conn = build_and_start_connector(client_id=0)
    broker = IBBroker(ib_connector=conn)

    broker.subscribe_to_new_orders(func=open_orders_printout)
    # broker.subscribe_to_order_status(func=order_status_printout)

    input("Press Enter to exit.")


def open_orders_printout(*args, **kwargs):
    print(f"\norder id: {args[0]}")
    print(f"contract: {args[1]}")
    print(f"order: {args[2]}")
    print(f"order status: {args[3].status}")


def order_status_printout(*args, **kwargs):
    pass


if __name__ == "__main__":
    monitor()
