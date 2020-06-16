import time
from datetime import datetime, date
from typing import Optional, Callable, Any, Tuple, Dict
from threading import Lock
from queue import Queue
import logging

from ibapi.contract import Contract as IbContract
from ibapi.order import Order as IbOrder
from ibapi.account_summary_tags import AccountSummaryTags

from algotradepy.brokers.base import ABroker
from algotradepy.connectors.ib_connector import (
    IBConnector,
    build_and_start_connector,
    SERVER_BUFFER_TIME,
    MASTER_CLIENT_ID,
)
from algotradepy.contracts import (
    AContract,
    StockContract,
    OptionContract,
    Exchange,
    Currency,
)
from algotradepy.orders import (
    MarketOrder,
    AnOrder,
    LimitOrder,
    OrderStatus,
    OrderAction,
)


_IB_FULL_DATE_FORMAT = "%Y%m%d"
_IB_MONTH_DATE_FORMAT = "%Y%m"


def _get_opt_trade_date(last_trade_date_str) -> date:
    try:
        dt = datetime.strptime(last_trade_date_str, _IB_FULL_DATE_FORMAT)
    except ValueError:
        dt = datetime.strptime(last_trade_date_str, _IB_MONTH_DATE_FORMAT)

    date_ = dt.date()

    return date_


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

    Notes
    -----
    - TODO: Consider moving all server-related logic out of this class
      (e.g. all of the request handling functionality, and req_id).
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

        self._tws_orders_associated = False

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

    def subscribe_to_new_orders(
        self, func: Callable, fn_kwargs: Optional[Dict] = None,
    ):
        f"""Subscribe to being notified of all newly created orders.

        The orders are transmitted only if they were successfully submitted.

        Parameters
        ----------
        func : Callable
            The function to which to feed the bars. It must accept {AContract}
            and {AnOrder} as its sole positional arguments.
        fn_kwargs : Dict
            Keyword arguments to feed to the callback function along with the
            bars.
        """
        if fn_kwargs is None:
            fn_kwargs = {}

        self._gain_control_of_tws_orders()

        def submitted_order_filter(
            order_id, ib_contract, ib_order, order_state
        ):
            if order_state.status == "Submitted":
                contract = self._from_ib_contract(ib_contract=ib_contract)
                order = self._from_ib_order(
                    order_id=order_id, ib_order=ib_order
                )
                if contract is not None and order is not None:
                    func(contract, order, **fn_kwargs)

        self._gain_control_of_tws_orders()
        self._ib_conn.subscribe(
            target_fn=self._ib_conn.openOrder,
            callback=submitted_order_filter,
            include_target_args=True,
        )

    # ------------------------ TODO: add to ABroker ----------------------------

    def subscribe_to_order_updates(
        self, func: Callable, fn_kwargs: Optional[Dict] = None,
    ):
        """Subscribe to receiving updates on orders' status.

        Parameters
        ----------
        func : Callable
            The callback function. It must accept an OrderStatus as its sole
            positional argument.
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
            *_,
            **__,
        ):
            if status in ["Submitted", "Cancelled", "Filled"]:
                status = OrderStatus(
                    order_id=order_id,
                    status=status,
                    filled=filled,
                    remaining=remaining,
                    ave_fill_price=ave_fill_price,
                )
                func(status, **fn_kwargs)

        self._gain_control_of_tws_orders()
        self._ib_conn.subscribe(
            target_fn=self._ib_conn.orderStatus, callback=order_status_filter,
        )

    def place_order(
        self, contract: AContract, order: AnOrder,
    ) -> Tuple[bool, int]:
        placed: Optional[bool] = None

        order_id = self._get_next_req_id()
        ib_contract = self._to_ib_contract(contract=contract)
        ib_contract.conId = 0
        ib_order = self._to_ib_order(order=order)
        ib_order.orderId = 0

        def _update_status(id_: int, status_: str, *args):
            nonlocal placed
            nonlocal order_id

            if id_ == order_id and placed is None:
                if status_ == "Submitted":
                    placed = True
                elif status_ == "Cancelled":
                    placed = False

        self._ib_conn.subscribe(
            target_fn=self._ib_conn.orderStatus, callback=_update_status,
        )
        self._ib_conn.placeOrder(
            orderId=order_id, contract=ib_contract, order=ib_order,
        )

        while placed is None:
            time.sleep(SERVER_BUFFER_TIME)

        self._ib_conn.unsubscribe(
            target_fn=self._ib_conn.orderStatus, callback=_update_status,
        )

        return placed, order_id

    def cancel_order(self, order_id):
        self._ib_conn.cancelOrder(orderId=order_id)

    # --------------------------------------------------------------------------

    def get_position(
        self, symbol: str, *args, account: Optional[str] = None, **kwargs
    ) -> int:
        # TODO: refactor with AContract
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

    # ------------------------ Req ID Helpers ----------------------------------

    def _get_next_req_id(self) -> int:
        if self._req_id is None:
            self._get_req_id_from_ib()
            self._req_id -= 1
        self._req_id += 1
        return self._req_id

    def _get_req_id_from_ib(self):
        args, _ = self._make_one_shot_request(
            ib_request_fn=self._ib_conn.reqIds,
            ib_receiver_fn=self._ib_conn.nextValidId,
            request_kwargs={"numIds": 1},
        )
        self._req_id = args[0]

    # ------------------------ Position Helpers --------------------------------

    def _subscribe_to_positions(self):
        request_positions = False

        with self._positions_lock:
            if self._positions is None:
                self._positions = {}
                request_positions = True

        if request_positions:
            # This is not quite an accumulation request, but a common
            # abstraction can be found.
            self._ib_conn.subscribe(
                target_fn=self._ib_conn.position,
                callback=self._update_position,
            )
            end_queue = self._get_callback_queue(
                ib_receiver_fn=self._ib_conn.positionEnd,
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
        with self._positions_lock:
            symbol_pos = self._positions.setdefault(symbol, {})
            symbol_pos_acc = symbol_pos.setdefault(account, {})
            symbol_pos_acc["position"] = position
            symbol_pos_acc["ave_cost"] = avg_cost

    # -------------------- Contract & Order Helpers ----------------------------

    def _gain_control_of_tws_orders(self):
        """Associates this broker with all orders placed through TWS.

        The IB Connector must have ID 0 to be eligible for this action.
        """
        if self._ib_conn.client_id != 0:
            raise ValueError(
                f"The {IBConnector} client ID must be 0. Current client ID"
                f" is {self._ib_conn.client_id}."
            )
        if not self._tws_orders_associated:
            self._ib_conn.reqAutoOpenOrders(bAutoBind=True)
            self._tws_orders_associated = True

    @staticmethod
    def _from_ib_contract(ib_contract: IbContract):
        contract = None

        if ib_contract.secType == "STK":
            contract = StockContract(
                con_id=ib_contract.conId, symbol=ib_contract.symbol,
            )
        elif ib_contract.secType == "OPT":
            last_trade_date = _get_opt_trade_date(
                last_trade_date_str=ib_contract.lastTradeDateOrContractMonth,
            )
            contract = OptionContract(
                con_id=ib_contract.conId,
                symbol=ib_contract.symbol,
                strike=ib_contract.strike,
                right=ib_contract.right,
                multiplier=ib_contract.multiplier,
                last_trade_date=last_trade_date,
            )
        else:
            logging.warning(
                f"Contract type {ib_contract.secType} not understood."
                f" No contract was built."
            )

        return contract

    @staticmethod
    def _from_ib_order(order_id: int, ib_order: IbOrder) -> Optional[AnOrder]:
        order = None
        if ib_order.action == "BUY":
            order_action = OrderAction.BUY
        elif ib_order.action == "SELL":
            order_action = OrderAction.SELL
        else:
            raise ValueError(f"Unknown order action {ib_order.action}.")

        if ib_order.orderType == "MKT":
            order = MarketOrder(
                order_id=order_id,
                action=order_action,
                quantity=ib_order.totalQuantity,
            )
        elif ib_order.orderType == "LMT":
            order = LimitOrder(
                order_id=order_id,
                action=order_action,
                quantity=ib_order.totalQuantity,
                limit_price=ib_order.lmtPrice,
            )
        else:
            logging.warning(
                f"Order type {ib_order.orderType} not understood."
                f" No order was built."
            )

        return order

    @staticmethod
    def _to_ib_contract(contract: AContract) -> IbContract:
        ib_contract = IbContract()
        if contract.con_id is not None:
            ib_contract.conId = contract.con_id
        ib_contract.symbol = contract.symbol
        if contract.currency == Currency.USD:
            ib_contract.currency = "USD"
        else:
            raise ValueError(f"Unknown currency {contract.currency}.")
        if contract.exchange == Exchange.SMART or contract.exchange is None:
            ib_contract.exchange = "SMART"
        else:
            raise ValueError(f"Unknown exchange {contract.exchange}.")

        if isinstance(contract, StockContract):
            ib_contract.secType = "STK"
        elif isinstance(contract, OptionContract):
            ib_contract.secType = "OPT"
            ib_contract.strike = contract.strike
            ib_contract.right = contract.right
        else:
            raise TypeError(f"Unknown type of contract {type(contract)}.")

        return ib_contract

    @staticmethod
    def _to_ib_order(order: AnOrder) -> IbOrder:
        ib_order = IbOrder()
        if order.action == OrderAction.BUY:
            ib_order.action = "BUY"
        elif order.action == OrderAction.SELL:
            ib_order.action = "SELL"
        else:
            raise ValueError(f"Unknown order action {order.action}.")
        ib_order.totalQuantity = order.quantity
        if order.order_id is not None:
            ib_order.orderId = order.order_id

        if isinstance(order, MarketOrder):
            ib_order.orderType = "MKT"
        elif isinstance(order, LimitOrder):
            ib_order.orderType = "LMT"
            ib_order.lmtPrice = order.limit_price
        else:
            raise TypeError(f"Unknown type of order {type(order)}.")

        return ib_order

    # ------------------------ Request Helpers ---------------------------------

    def _make_accumulation_request(
        self,
        ib_request_fn: Callable,
        ib_receiver_fn: Callable,
        ib_end_fn: Callable,
        ib_cancel_fn: Optional[Callable] = None,
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

        if ib_cancel_fn is not None:
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
            time.sleep(SERVER_BUFFER_TIME)
        res = queue.get()

        return res
