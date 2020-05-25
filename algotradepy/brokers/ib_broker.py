from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from threading import Thread
from queue import Queue

from algotradepy.brokers.base import ABroker
from algotradepy.connectors.ib_connector import IBConnector

from ibapi.account_summary_tags import AccountSummaryTags


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
            self._ib_conn = IBConnector(trading_mode=trading_mode)
        else:
            self._ib_conn = ib_connector
        connector_thread = Thread(target=self._ib_conn.run)
        connector_thread.start()
        self._req_id = None

    def __del__(self):
        self._ib_conn.stop()

    @property
    def acc_cash(self) -> float:
        req_id = self._get_next_req_id()
        acc_summary_results_queue = self._get_results_queue(
            ib_receiver_fn=self._ib_conn.accountSummary,
            req_id=req_id,
        )
        acc_summary_end_queue = self._get_results_queue(
            ib_receiver_fn=self._ib_conn.accountSummaryEnd,
            req_id=req_id,
        )
        self._ib_conn.reqAccountSummary(
            reqId=req_id,
            groupName="All",
            tags=AccountSummaryTags.TotalCashValue,
        )
        self._await_results_from_queue(queue=acc_summary_end_queue)
        args, kwargs = self._await_results_from_queue(
            queue=acc_summary_results_queue,
        )
        acc_summary = args
        self._ib_conn.cancelAccountSummary(reqId=req_id)
        acc_value = float(acc_summary[3])
        return acc_value

    @property
    def datetime(self) -> datetime:
        server_time_queue = self._get_results_queue(
            ib_receiver_fn=self._ib_conn.currentTime,
        )
        self._ib_conn.reqCurrentTime()
        args, kwargs = self._await_results_from_queue(queue=server_time_queue)
        server_time = args[0]
        dt = datetime.fromtimestamp(server_time)
        return dt

    def subscribe_for_bars(
            self,
            symbol: str,
            bar_size: timedelta,
            func: Callable,
            fn_kwargs: Optional[dict] = None,
    ):
        raise NotImplementedError

    def get_position(self, symbol: str) -> int:
        pass

    def buy(self, symbol: str, n_shares: int, **kwargs) -> bool:
        pass

    def sell(self, symbol: str, n_shares: int, **kwargs) -> bool:
        pass

    def get_transaction_fee(self) -> float:
        pass

    # ------------ todo: add to ABroker -----------------

    def subscribe_to_new_positions(
            self,
            func: Callable,
            fn_kwargs: Optional[dict] = None,
    ):
        if fn_kwargs is None:
            fn_kwargs = {}
        self._ib_conn.subscribe(
            target_fn=self._ib_conn.openOrder,
            callback=func,
            include_target_args=True,
            callback_kwargs=fn_kwargs,
        )
        self._ib_conn.reqAutoOpenOrders(bAutoBind=True)

    def _get_next_req_id(self) -> int:
        if self._req_id is None:
            self._get_req_id_from_ib()
            self._req_id -= 1
        self._req_id += 1
        return self._req_id

    def _get_req_id_from_ib(self):
        queue = self._get_results_queue(
            ib_receiver_fn=self._ib_conn.nextValidId,
        )
        self._ib_conn.reqIds(numIds=1)
        args, kwargs = self._await_results_from_queue(queue=queue)
        self._req_id = args[0]

    def _get_results_queue(
            self,
            ib_receiver_fn: Callable,
            req_id: Optional[int] = None,
    ):
        receiver_queue = Queue()
        self._ib_conn.subscribe(
            target_fn=ib_receiver_fn,
            callback=self._update_queue,
            callback_kwargs={
                "queue": receiver_queue,
                "req_id": req_id
            },
        )
        return receiver_queue

    @staticmethod
    def _update_queue(*args, queue: Queue, req_id: Optional[int], **kwargs):
        if req_id is None or args[0] == req_id:
            queue.put((args, kwargs))

    @staticmethod
    def _await_results_from_queue(queue: Queue) -> Any:
        while queue.empty():
            pass
        res = queue.get()
        return res

