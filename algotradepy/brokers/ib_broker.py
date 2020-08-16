from datetime import datetime
from typing import Optional, Tuple, Dict, List, Callable

from algotradepy.ib_utils import IBBase
from algotradepy.position import Position

try:
    import ib_insync
except ImportError:
    raise ImportError(
        "Optional package ib_insync not install. Please install"
        " using 'pip install ib_insync'."
    )
from ibapi.account_summary_tags import (
    AccountSummaryTags as _AccountSummaryTags,
)
from ib_insync.order import Trade as _IBTrade

from algotradepy.brokers.base import ABroker
from algotradepy.connectors.ib_connector import (
    IBConnector,
    MASTER_CLIENT_ID,
    SERVER_BUFFER_TIME,
)
from algotradepy.contracts import (
    AContract,
    are_loosely_equal_contracts,
)
from algotradepy.trade import Trade


class IBBroker(IBBase, ABroker):
    """Interactive Brokers Broker class.

    This class implements the ABroker interface for use with the Interactive
    Brokers API. It is an adaptor to the IBConnector, exposing the relevant
    methods.

    Parameters
    ----------
    simulation : bool, default True
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
        ABroker.__init__(self, simulation=simulation)
        IBBase.__init__(self, simulation=simulation, ib_connector=ib_connector)

    @property
    def acc_cash(self) -> float:
        acc_summary = self._ib_conn.accountSummary()
        acc_values = []

        for s in acc_summary:
            if s.tag == _AccountSummaryTags.TotalCashValue:
                acc_values.append(float(s.value))

        acc_value = sum(acc_values)

        return acc_value

    @property
    def datetime(self) -> datetime:
        dt = self._ib_conn.reqCurrentTime()
        dt = dt.astimezone()  # localize the timezone
        return dt

    @property
    def trades(self) -> List[Trade]:
        ib_trades = self._ib_conn.trades()
        trades = [
            self._from_ib_trade(ib_trade=ib_trade) for ib_trade in ib_trades
        ]
        return trades

    @property
    def open_trades(self) -> List[Trade]:
        open_ib_trades = self._ib_conn.openTrades()
        open_trades = [
            self._from_ib_trade(ib_trade=ib_trade)
            for ib_trade in open_ib_trades
        ]
        return open_trades

    @property
    def open_positions(self) -> List[Position]:
        # TODO: test
        ib_positions = self._ib_conn.positions()
        positions = [
            self._from_ib_position(ib_position=ib_pos)
            for ib_pos in ib_positions
        ]
        return positions

    def subscribe_to_new_trades(
        self, func: Callable, fn_kwargs: Optional[Dict] = None,
    ):
        if fn_kwargs is None:
            fn_kwargs = {}

        def submitted_order_filter(ib_trade: _IBTrade):
            trade = self._from_ib_trade(ib_trade=ib_trade)
            func(trade, **fn_kwargs)

        self._ib_conn.openOrderEvent += submitted_order_filter

    def subscribe_to_trade_updates(
        self, func: Callable, fn_kwargs: Optional[Dict] = None,
    ):
        if fn_kwargs is None:
            fn_kwargs = {}

        def order_status_filter(ib_trade: _IBTrade):
            status = self._from_ib_status(ib_order_status=ib_trade.orderStatus)
            func(status, **fn_kwargs)

        self._ib_conn.orderStatusEvent += order_status_filter

    def place_trade(
        self, trade: Trade, *args, await_confirm: bool = False,
    ) -> Tuple[bool, Trade]:
        ib_contract = self._to_ib_contract(contract=trade.contract)
        ib_order = self._to_ib_order(order=trade.order)

        ib_trade = self._ib_conn.placeOrder(
            contract=ib_contract, order=ib_order,
        )

        placed = True
        confirmed = False
        while await_confirm and not confirmed:
            status = ib_trade.orderStatus.status
            if "Submitted" in status or status == "Filled":
                placed = True
                confirmed = True
            elif "Cancelled" in status:
                placed = False
                confirmed = True
            self.sleep(SERVER_BUFFER_TIME)

        trade = self._from_ib_trade(ib_trade=ib_trade)

        return placed, trade

    def cancel_trade(self, trade: Trade):
        ib_order = self._to_ib_order(order=trade.order)
        self._ib_conn.cancelOrder(order=ib_order)

    def get_position(
        self,
        contract: AContract,
        *args,
        account: Optional[str] = None,
        **kwargs,
    ) -> float:
        if self._ib_conn.client_id != MASTER_CLIENT_ID:
            raise AttributeError(
                f"This client ID cannot request positions. Please use a broker"
                f" instantiated with the master client ID ({MASTER_CLIENT_ID})"
                f" to request positions."
            )

        if account is None:
            account = ""

        pos = 0
        positions = self._ib_conn.positions(account=account)
        for position in positions:
            pos_contract = self._from_ib_contract(
                ib_contract=position.contract
            )
            if are_loosely_equal_contracts(
                loose=contract, well_defined=pos_contract,
            ):
                pos = position.position
                break

        return pos

    def get_transaction_fee(self) -> float:
        # TODO: implement
        raise NotImplementedError
