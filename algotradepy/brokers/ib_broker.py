from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Tuple, Dict
from threading import Lock
from queue import Queue
import logging

from ibapi.contract import Contract as IbContract
from ibapi.order import Order as IbOrder

from algotradepy.brokers.base import ABroker
from algotradepy.connectors.ib_connector import (
    IBConnector,
    build_and_start_connector,
    MASTER_CLIENT_ID,
)

from ibapi.account_summary_tags import AccountSummaryTags

from algotradepy.orders import MarketOrder, AnOrder, LimitOrder, OrderStatus


class IBBroker(ABroker):
    """Interactive Brokers Broker class.

    This class implements the ABroker interface for use with the Interactive
    Brokers API. It is an adaptor to the IBConnector, exposing the relevant
    methods.

    Parameters
    ----------
    simulation : bool, default True
        TODO: link to ABroker docs
        Ignored if parameter `ib_connector` is supplied.
    ib_connector : IBConnector, optional, default None
        A custom instance of the `IBConnector` can be supplied. If not provided,
        it is assumed that the receiver is TWS (see `IBConnector`'s
        documentation for more details).
    """

    def __init__(
        self,
        simulation: bool = True,
        ib_connector: Optional[IBConnector] = None,
    ):
        super().__init__(simulation=simulation)
        if ib_connector is None:
            if simulation:
                trading_mode = "paper"
            else:
                trading_mode = "live"
            self._ib_conn = build_and_start_connector(
                trading_mode=trading_mode
            )
        else:
            self._ib_conn = ib_connector
        self._req_id: Optional[int] = None
        self._positions: Optional[Dict] = None
        self._positions_lock = Lock()

    def __del__(self):
        if self._positions is not None:
            self._ib_conn.cancelPositions()
        self._ib_conn.managed_disconnect()

    @property
    def acc_cash(self) -> float:
        args, kwargs = self._make_accumulation_request(
            ib_request_fn=self._ib_conn.reqAccountSummary,
            request_kwargs={
                "groupName": "All",
                "tags": AccountSummaryTags.TotalCashValue,
            },
            ib_receiver_fn=self._ib_conn.accountSummary,
            ib_end_fn=self._ib_conn.accountSummaryEnd,
            ib_cancel_fn=self._ib_conn.cancelAccountSummary,
        )
        acc_summary = args
        acc_value = float(acc_summary[3])

        return acc_value

    @property
    def datetime(self) -> datetime:
        args, kwargs = self._make_one_shot_request(
            ib_request_fn=self._ib_conn.reqCurrentTime,
            ib_receiver_fn=self._ib_conn.currentTime,
        )
        server_time = args[0]
        dt = datetime.fromtimestamp(server_time)

        return dt

    def subscribe_to_bars(
        self,
        symbol: str,
        bar_size: timedelta,
        func: Callable,
        fn_kwargs: Optional[dict] = None,
    ):
        # TODO: implement.
        # TODO: test.
        raise NotImplementedError

    def subscribe_to_new_orders(
        self, func: Callable, fn_kwargs: Optional[Dict] = None
    ):
        if fn_kwargs is None:
            fn_kwargs = {}

        def submitted_order_filter(
            order_id, contract, order, order_state,
        ):
            # TODO: test case.
            if order_state.status == "Submitted":
                order = self._build_order(
                    order_id=order_id, ib_contract=contract, ib_order=order,
                )
                if order is not None:
                    func(order, **fn_kwargs)

        self._ib_conn.subscribe(
            target_fn=self._ib_conn.openOrder,
            callback=submitted_order_filter,
            include_target_args=True,
        )
        self._ib_conn.reqAutoOpenOrders(bAutoBind=True)

    # ------------------------ TODO: add to ABroker ----------------------------

    def subscribe_to_order_fill_updates(
        self, func: Callable, fn_kwargs: Optional[Dict] = None
    ):
        """Subscribe to receiving updates on orders' fill status.

        Parameters
        ----------
        func : Callable
            The callback function. It must accept the order ID int and the
        fn_kwargs : dict
            The keyword arguments to pass to the callback function along with
            the positional arguments.
        """
        if fn_kwargs is None:
            fn_kwargs = {}

        def order_status_filter(
            order_id: int,
            status: str,
            filled: float,
            remaining: float,
            ave_fill_price: float,
            *args,
        ):
            if status == "Filled":
                status = OrderStatus(
                    order_id=order_id,
                    filled=filled,
                    remaining=remaining,
                    ave_fill_price=ave_fill_price,
                )
                func(status, **fn_kwargs)

        self._ib_conn.subscribe(
            target_fn=self._ib_conn.orderStatus,
            callback=order_status_filter,
            include_target_args=True,
        )

    # --------------------------------------------------------------------------

    def get_position(
        self, symbol: str, *args, account: Optional[str] = None, **kwargs
    ) -> int:
        if self._ib_conn.client_id != MASTER_CLIENT_ID:
            raise AttributeError(
                f"This client ID cannot request positions. Please use a broker"
                f" instantiated with the master client ID ({MASTER_CLIENT_ID})"
                f" to request positions."
            )

        pos = 0

        if self._positions is None:
            self._subscribe_to_positions()

        symbol_dict: Optional[Dict] = self._positions.get(symbol)
        if symbol_dict is not None:
            if account is None:
                for acc, acc_dict in symbol_dict.items():
                    pos += acc_dict["position"]
            else:
                pos += symbol_dict[account]["position"]

        return pos

    def buy(self, symbol: str, n_shares: float, **kwargs) -> bool:
        # TODO: implement.
        # TODO: test.
        raise NotImplementedError

    def limit_buy(
        self, symbol: str, n_shares: float, limit_price: float, **kwargs
    ):
        raise NotImplementedError

    def sell(self, symbol: str, n_shares: float, **kwargs) -> bool:
        # TODO: implement.
        # TODO: test.
        raise NotImplementedError

    def get_transaction_fee(self) -> float:
        # TODO: implement.
        # TODO: test.
        raise NotImplementedError

    def gain_control_of_tws_orders(self):
        if self._ib_conn.client_id != 0:
            raise ValueError(
                f"The {IBConnector} client ID must be 0. Current client ID"
                f" is {self._ib_conn.client_id}."
            )
        self._ib_conn.reqAutoOpenOrders(bAutoBind=True)

    def _make_accumulation_request(
        self,
        ib_request_fn: Callable,
        ib_receiver_fn: Callable,
        ib_end_fn: Callable,
        ib_cancel_fn: Callable,
        request_kwargs: Optional[Dict] = None,
    ) -> Tuple[Tuple, Dict]:
        if request_kwargs is None:
            request_kwargs = {}
        req_id = self._get_next_req_id()
        results_queue = self._get_callback_queue(
            ib_receiver_fn=ib_receiver_fn, req_id=req_id,
        )
        end_queue = self._get_callback_queue(
            ib_receiver_fn=ib_end_fn, req_id=req_id,
        )
        request_kwargs["reqId"] = req_id

        ib_request_fn(**request_kwargs)
        self._await_results_from_queue(queue=end_queue)
        args, kwargs = self._await_results_from_queue(queue=results_queue)
        ib_cancel_fn(req_id)

        return args, kwargs

    def _make_one_shot_request(
        self,
        ib_request_fn: Callable,
        ib_receiver_fn: Callable,
        request_kwargs: Optional[Dict] = None,
    ) -> Tuple[Tuple, Dict]:
        if request_kwargs is None:
            request_kwargs = {}
        results_queue = self._get_callback_queue(
            ib_receiver_fn=ib_receiver_fn,
        )

        ib_request_fn(**request_kwargs)
        args, kwargs = self._await_results_from_queue(queue=results_queue)

        return args, kwargs

    def _get_next_req_id(self) -> int:
        if self._req_id is None:
            self._get_req_id_from_ib()
            self._req_id -= 1
        self._req_id += 1
        return self._req_id

    def _get_req_id_from_ib(self):
        queue = self._get_callback_queue(
            ib_receiver_fn=self._ib_conn.nextValidId,
        )
        self._ib_conn.reqIds(numIds=1)
        args, kwargs = self._await_results_from_queue(queue=queue)
        self._req_id = args[0]

    def _get_callback_queue(
        self, ib_receiver_fn: Callable, req_id: Optional[int] = None,
    ):
        receiver_queue = Queue()
        self._ib_conn.subscribe(
            target_fn=ib_receiver_fn,
            callback=self._update_queue,
            callback_kwargs={"queue": receiver_queue, "req_id": req_id},
        )

        return receiver_queue

    @staticmethod
    def _update_queue(*args, queue: Queue, req_id: Optional[int], **kwargs):
        if req_id is None or (len(args) != 0 and args[0] == req_id):
            queue.put((args, kwargs))

    @staticmethod
    def _await_results_from_queue(queue: Queue) -> Any:
        while queue.empty():
            pass
        res = queue.get()

        return res

    def _subscribe_to_positions(self):
        request_positions = False

        with self._positions_lock:
            if self._positions is None:
                self._positions = {}
                request_positions = True

        if request_positions:
            self._ib_conn.subscribe(
                target_fn=self._ib_conn.position,
                callback=self._update_position,
            )
            end_queue = self._get_callback_queue(
                ib_receiver_fn=self._ib_conn.positionEnd,
                # req_id=-1,  # just to have something returned in the queue
            )
            self._ib_conn.reqPositions()
            self._await_results_from_queue(queue=end_queue)

    def _update_position(
        self,
        account: str,
        contract: IbContract,
        position: float,
        avg_cost: float,
    ):
        symbol = contract.symbol
        print(f"Updating positions {account} {contract.symbol}")
        with self._positions_lock:
            symbol_pos = self._positions.setdefault(symbol, {})
            symbol_pos_acc = symbol_pos.setdefault(account, {})
            symbol_pos_acc["position"] = position
            symbol_pos_acc["ave_cost"] = avg_cost

    @staticmethod
    def _build_order(
        order_id: int, ib_contract: IbContract, ib_order: IbOrder,
    ) -> Optional[AnOrder]:
        order = None

        if ib_order.orderType == "MKT":
            order = MarketOrder(
                order_id=order_id,
                symbol=ib_contract.symbol,
                action=ib_order.action,
                quantity=ib_order.totalQuantity,
                sec_type=ib_contract.secType,
            )
        elif ib_order.orderType == "LMT":
            order = LimitOrder(
                order_id=order_id,
                symbol=ib_contract.symbol,
                action=ib_order.action,
                quantity=ib_order.totalQuantity,
                sec_type=ib_contract.secType,
                limit_price=ib_order.lmtPrice,
            )
        else:
            logging.warning(
                f"Order type {ib_order.orderType} not understood."
                f" No order was built."
            )

        return order
