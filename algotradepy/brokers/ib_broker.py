import time
import calendar
from datetime import datetime, date
from typing import Optional, Callable, Any, Tuple, Dict
from threading import Lock
from queue import Queue
import logging

from ibapi.common import UNSET_DOUBLE
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
    Right,
    PriceType,
)
from algotradepy.orders import (
    MarketOrder,
    AnOrder,
    LimitOrder,
    OrderStatus,
    OrderAction,
    OrderState,
    TrailingStopOrder,
)


_IB_FULL_DATE_FORMAT = "%Y%m%d"
_IB_MONTH_DATE_FORMAT = "%Y%m"


def _get_opt_trade_date(last_trade_date_str) -> date:
    try:
        dt = datetime.strptime(last_trade_date_str, _IB_FULL_DATE_FORMAT)
        date_ = dt.date()
    except ValueError:
        # month-only, set to last day of month
        dt = datetime.strptime(last_trade_date_str, _IB_MONTH_DATE_FORMAT)
        date_ = dt.date()
        last_day_of_month = calendar.monthrange(dt.year, dt.month)
        date_ = date(date_.year, date_.month, last_day_of_month)

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

    _ask_tick_types = [1, 67]
    _bid_tick_types = [2, 66]

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
        self._price_subscriptions: Optional[Dict] = None

        self._tws_orders_associated = False
        self._market_data_type_set = False

        self._get_next_req_id()

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

    def subscribe_to_new_trades(
        self, func: Callable, fn_kwargs: Optional[Dict] = None,
    ):
        if fn_kwargs is None:
            fn_kwargs = {}

        self._gain_control_of_tws_orders()

        def submitted_order_filter(
            order_id, ib_contract, ib_order, order_state
        ):
            if "Submitted" in order_state.status:
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

    def subscribe_to_trade_updates(
        self, func: Callable, fn_kwargs: Optional[Dict] = None,
    ):
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
            state = self._from_ib_state(status=status)
            status = OrderStatus(
                order_id=order_id,
                state=state,
                filled=filled,
                remaining=remaining,
                ave_fill_price=ave_fill_price,
            )
            func(status, **fn_kwargs)

        self._gain_control_of_tws_orders()
        self._ib_conn.subscribe(
            target_fn=self._ib_conn.orderStatus, callback=order_status_filter,
        )

    def subscribe_to_tick_data(
        self,
        contract: AContract,
        func: Callable,
        fn_kwargs: Optional[Dict] = None,
        price_type: PriceType = PriceType.MARKET,
    ):
        # TODO: test
        if fn_kwargs is None:
            fn_kwargs = {}

        self._set_market_data_type()

        req_id = self._get_next_req_id()
        ib_contract = self._to_ib_contract(contract=contract)

        def _price_update(id_: int, tick_type_: int, price_: float, *_):
            if id_ in self._price_subscriptions:
                price_sub = self._price_subscriptions[id_]
                conntract_ = price_sub["contract"]

                if tick_type_ in self._ask_tick_types:
                    price_sub["ask"] = price_
                    if price_sub["price_type"] == PriceType.ASK:
                        func(conntract_, price_, **fn_kwargs)
                elif tick_type_ in self._bid_tick_types:
                    price_sub["bid"] = price_
                    if price_sub["price_type"] == PriceType.BID:
                        func(conntract_, price_, **fn_kwargs)

                if (
                    price_sub["price_type"] == PriceType.MARKET
                    and price_sub["ask"] is not None
                    and price_sub["bid"] is not None
                ):
                    price_ = (price_sub["ask"] + price_sub["bid"]) / 2
                    func(conntract_, price_, **fn_kwargs)
                    price_sub["ask"] = None
                    price_sub["bid"] = None

        self._price_subscriptions[req_id] = {
            "contract": contract,
            "func": func,
            "price_type": price_type,
            "ask": None,
            "bid": None,
        }
        self._ib_conn.subscribe(
            target_fn=self._ib_conn.tickPrice, callback=_price_update,
        )
        self._ib_conn.reqMktData(
            reqId=req_id,
            contract=ib_contract,
            genericTickList="",
            snapshot=False,
            regulatorySnapshot=False,
            mktDataOptions=[],
        )

    def cancel_tick_data(self, contract: AContract, func: Callable):
        # TODO: test
        if self._market_data_type_set is None:
            raise RuntimeError("No price subscriptions were requested.")

        found = False
        for req_id, sub_dict in self._price_subscriptions.items():
            if contract == sub_dict["contract"] and func == sub_dict["func"]:
                self._ib_conn.cancelMktData(reqId=req_id)
                self._ib_conn.unsubscribe(
                    target_fn=self._ib_conn.tickPrice, callback=func,
                )
                del self._price_subscriptions[req_id]
                found = True
                break

        if not found:
            raise ValueError(
                f"No price subscription found for contract {contract} and"
                f" function {func}."
            )

    # ------------------------ TODO: add to ABroker ----------------------------

    def place_order(
        self,
        contract: AContract,
        order: AnOrder,
        *args,
        await_confirm: bool = False,
    ) -> Tuple[bool, int]:
        """Place an order with specified details.

        Parameters
        ----------
        contract : AContract
            The contract definition for the order.
        order : AnOrder
            The remaining details of the order definition.
        await_confirm : bool, default False
            If set to true, will await confirmation from the server that the
            order was placed. If used in a call that was triggered as a response
            to a message received from the server, will make the thread hang.
            TODO: fix.....
        Returns
        -------
        tuple of bool and int
            The tuple indicates if the order has been successfully placed,
            whereas the int is the associated order-id.
        """
        placed: Optional[bool] = None

        order_id = self._get_next_req_id()
        ib_contract = self._to_ib_contract(contract=contract)
        ib_order = self._to_ib_order(order=order)

        def _update_status(id_: int, status_: str, *args):
            nonlocal placed
            nonlocal order_id

            if id_ == order_id and placed is None:
                if "Submitted" in status_ or status_ == "Filled":
                    placed = True
                elif "Cancelled" in status_:
                    placed = False

        if await_confirm:
            self._ib_conn.subscribe(
                target_fn=self._ib_conn.orderStatus, callback=_update_status,
            )

        self._ib_conn.placeOrder(
            orderId=order_id, contract=ib_contract, order=ib_order,
        )

        if await_confirm:
            while placed is None:
                time.sleep(SERVER_BUFFER_TIME)
            self._ib_conn.unsubscribe(
                target_fn=self._ib_conn.orderStatus, callback=_update_status,
            )
        else:
            placed = True

        return placed, order_id

    def cancel_order(self, order_id):
        self._ib_conn.cancelOrder(orderId=order_id)

    # --------------------------------------------------------------------------

    def get_position(
        self,
        contract: AContract,
        *args,
        account: Optional[str] = None,
        **kwargs,
    ) -> float:
        """Get the current position for the specified symbol.

        Parameters
        ----------
        contract : AContract
            The contract definition for which the position is required.
        account : str, optional, default None
            The account for which the position is requested. If not specified,
            all accounts' positions for that symbol are summed.

        Returns
        -------
        pos : float
            The position for the specified symbol.
        """
        if self._ib_conn.client_id != MASTER_CLIENT_ID:
            raise AttributeError(
                f"This client ID cannot request positions. Please use a broker"
                f" instantiated with the master client ID ({MASTER_CLIENT_ID})"
                f" to request positions."
            )

        pos = 0

        if self._positions is None:
            self._subscribe_to_positions()

        symbol_dict: Optional[Dict] = self._positions.get(contract.symbol)
        if symbol_dict is not None:
            if account is None:
                for acc, acc_dict in symbol_dict.items():
                    pos += acc_dict["position"]
            else:
                pos += symbol_dict[account]["position"]
        else:
            pos = 0

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

    def _set_market_data_type(self):
        if not self._market_data_type_set:
            self._ib_conn.reqMarketDataType(marketDataType=4)
            self._market_data_type_set = True
            self._price_subscriptions = {}

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
            if ib_contract.right == "C":
                right = Right.CALL
            elif ib_contract.right == "P":
                right = Right.PUT
            else:
                raise ValueError(f"Unknown right type {ib_contract.right}.")
            contract = OptionContract(
                con_id=ib_contract.conId,
                symbol=ib_contract.symbol,
                strike=ib_contract.strike,
                right=right,
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
    def _to_ib_contract(contract: AContract) -> IbContract:
        ib_contract = IbContract()
        if contract.con_id is not None:
            ib_contract.conId = contract.con_id
        ib_contract.symbol = contract.symbol
        ib_contract.currency = contract.currency.value

        if contract.exchange is None:
            ib_contract.exchange = "SMART"
        elif contract.exchange == Exchange.NASDAQ:
            ib_contract.exchange = "ISLAND"
        else:
            ib_contract.exchange = contract.exchange.value

        if isinstance(contract, StockContract):
            ib_contract.secType = "STK"
        elif isinstance(contract, OptionContract):
            ib_contract.secType = "OPT"
            ib_contract.strike = contract.strike
            if contract.right == Right.CALL:
                ib_contract.right = "C"
            elif contract.right == Right.PUT:
                ib_contract.right = "P"
            else:
                raise ValueError(f"Unknown right type {contract.right}.")
            ib_contract.lastTradeDateOrContractMonth = contract.last_trade_date.strftime(
                _IB_FULL_DATE_FORMAT
            )
        else:
            raise TypeError(f"Unknown type of contract {type(contract)}.")

        return ib_contract

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
        elif ib_order.orderType == "TRAIL":
            if ib_order.trailingPercent == UNSET_DOUBLE:
                trailing_percent = None
            else:
                trailing_percent = ib_order.trailingPercent
            if ib_order.auxPrice == UNSET_DOUBLE:
                stop_price = None
            else:
                stop_price = ib_order.auxPrice

            order = TrailingStopOrder(
                order_id=order_id,
                action=order_action,
                quantity=ib_order.totalQuantity,
                trailing_percent=trailing_percent,
                stop_price=stop_price,
            )
        else:
            logging.warning(
                f"Order type {ib_order.orderType} not understood."
                f" No order was built."
            )

        return order

    @staticmethod
    def _to_ib_order(order: AnOrder) -> IbOrder:
        ib_order = IbOrder()
        ib_order.action = order.action.value
        ib_order.totalQuantity = order.quantity
        if order.order_id is not None:
            ib_order.orderId = order.order_id

        if isinstance(order, MarketOrder):
            ib_order.orderType = "MKT"
        elif isinstance(order, LimitOrder):
            ib_order.orderType = "LMT"
            ib_order.lmtPrice = round(order.limit_price, 2)
        elif isinstance(order, TrailingStopOrder):
            ib_order.orderType = "TRAIL"
            if order.stop_price is not None:
                ib_order.auxPrice = order.stop_price
            elif order.trailing_percent is not None:
                ib_order.trailingPercent = order.trailing_percent
        else:
            raise TypeError(f"Unknown type of order {type(order)}.")

        return ib_order

    @staticmethod
    def _from_ib_state(status: str) -> OrderState:
        if status == "ApiPending":
            state = OrderState.PENDING
        elif status == "PendingSubmit":
            state = OrderState.PENDING
        elif status == "PreSubmitted":
            state = OrderState.SUBMITTED
        elif status == "Submitted":
            state = OrderState.SUBMITTED
        elif status == "ApiCancelled":
            state = OrderState.CANCELLED
        elif status == "Cancelled":
            state = OrderState.CANCELLED
        elif status == "Filled":
            state = OrderState.FILLED
        elif status == "Inactive":
            state = OrderState.INACTIVE
        else:
            raise ValueError(f"Unknown IB order status {status}.")

        return state

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
