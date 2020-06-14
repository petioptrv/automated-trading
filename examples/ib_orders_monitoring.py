from algotradepy.brokers.ib_broker import IBBroker
from algotradepy.connectors.ib_connector import build_and_start_connector


def monitor():
    conn = build_and_start_connector(client_id=0)
    broker = IBBroker(ib_connector=conn)

    broker.subscribe_to_new_orders(func=open_orders_printout)
    broker.subscribe_to_order_updates(func=order_status_printout)

    print(f"exiting with {input('Press Enter to exit.')}")


def open_orders_printout(order, **kwargs):
    print("\nSUBMITTED ORDER")
    print("===============")
    print(f"order class: {type(order)}")
    print(f"order id: {order.order_id}")
    print(f"symbol: {order.symbol}")
    print(f"action: {order.action}")
    print(f"total quantity: {order.quantity}")
    print(f"sec type: {order.sec_type}")
    print(f"limit price: {order.limit_price}")


def order_status_printout(status, **kwargs):
    print("\nSTATUS")
    print("======")
    print(f"order id: {status.order_id}")
    print(f"status: {status.status}")
    print(f"filled: {status.filled}")
    print(f"remaining: {status.remaining}")
    print(f"ave fill price: {status.ave_fill_price}")


if __name__ == "__main__":
    monitor()
