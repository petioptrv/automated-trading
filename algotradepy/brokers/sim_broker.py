from datetime import datetime
import time as real_time
from typing import Callable, Optional, Dict, Tuple, List

from algotradepy.brokers.base import ABroker
from algotradepy.contracts import AContract, Currency
from algotradepy.objects import Position
from algotradepy.orders import (
    LimitOrder,
    OrderAction,
    MarketOrder,
)
from algotradepy.sim_utils import ASimulationPiece
from algotradepy.streamers.sim_streamer import SimulationDataStreamer
from algotradepy.trade import TradeState, TradeStatus, Trade
from algotradepy.utils import recursive_dict_update

DEFAULT_SIM_ACC = "DEFAULT"


class SimulationBroker(ABroker, ASimulationPiece):
    """Implements the broker interface for simulated back-testing.

    The simulation broker uses the
    :class:`~algotradepy.streamers.sim_streamer.SimulationDataStreamer` to
    provide simulated brokerage functionality allowing to back-test trading
    algorithms before taking them to a live-trading environment.

    Parameters
    ----------
    sim_streamer : SimulationDataStreamer
        The simulation data streamer object.
    starting_funds : float
        The funds with which the simulation will begin.
    transaction_cost : float
        The cost of each transaction.
    starting_positions : dict, optional, default None
        A dictionary of the starting positions, mapping each account to
        a dictionary of :class:`~algotradepy.contracts.AContract` to
        :class:`~algotradepy.objects.Position`.

    """

    def __init__(
        self,
        sim_streamer: SimulationDataStreamer,
        starting_funds: Dict[Currency, float],
        transaction_cost: float = 0,
        starting_positions: Optional[
            Dict[str, Dict[AContract, Position]]
        ] = None,
    ):
        ABroker.__init__(self, simulation=True)
        ASimulationPiece.__init__(self)

        self._streamer = sim_streamer
        self._cash = starting_funds
        # {account: {contract: Position}}
        self._positions: Dict[str, Dict[AContract, Position]] = {}
        if starting_positions is not None:
            self._positions = recursive_dict_update(
                receiver=self._positions, updater=starting_positions,
            )
        self._abs_fee = transaction_cost
        self._valid_id = 1
        self._new_trade_subscribers = []
        self._trade_updates_subscribers = []
        self._position_updates_subscribers = []
        self._placed_trades: List[Trade] = []
        # [(trade, price, n_shares)]
        self._scheduled_trade_executions = []

    @property
    def acc_cash(self) -> Dict[Currency, float]:
        return self._cash

    @property
    def datetime(self) -> datetime:
        return self.sim_clock.datetime

    @property
    def trades(self) -> List[Trade]:
        return self._placed_trades

    @property
    def open_trades(self) -> List[Trade]:
        # TODO: test
        done_statuses = [TradeState.CANCELLED, TradeState.FILLED]
        open_trades = []

        for trade in self._placed_trades:
            if trade.status.state not in done_statuses:
                open_trades.append(trade)

        return open_trades

    @property
    def open_positions(self) -> List[Position]:
        positions = [
            position for contract, position in self._positions.items()
        ]
        return positions

    def sleep(self, secs: float):
        real_time.sleep(secs=secs)

    def subscribe_to_new_trades(
        self, func: Callable, fn_kwargs: Optional[Dict] = None,
    ):
        # TODO: test
        if fn_kwargs is None:
            fn_kwargs = {}
        self._new_trade_subscribers.append((func, fn_kwargs))

    def subscribe_to_trade_updates(
        self, func: Callable, fn_kwargs: Optional[Dict] = None,
    ):
        # TODO: test
        if fn_kwargs is None:
            fn_kwargs = {}
        self._trade_updates_subscribers.append((func, fn_kwargs))

    def subscribe_to_position_updates(
        self, func: Callable, fn_kwargs: Optional[Dict] = None,
    ):
        # TODO: test
        if fn_kwargs is None:
            fn_kwargs = {}
        self._position_updates_subscribers.append((func, fn_kwargs))

    def place_trade(
        self,
        trade: Trade,
        *args,
        trade_execution_price: Optional[float] = None,
        trade_execution_size: Optional[float] = None,
        **kwargs,
    ) -> Tuple[bool, Trade]:
        trade_id = self._get_increment_valid_id()
        order = trade.order
        order._order_id = trade_id
        new_status = TradeStatus(
            state=TradeState.SUBMITTED,
            filled=0,
            remaining=order.quantity,
            ave_fill_price=0,
            order_id=trade_id,
        )
        new_trade = Trade(
            contract=trade.contract, order=order, status=new_status,
        )
        self._placed_trades.append(new_trade)

        self._update_trade_updates_subscribers(trade=new_trade)

        if isinstance(trade.order, MarketOrder):
            self._scheduled_trade_executions.append(
                (trade, trade_execution_price, trade_execution_size)
            )

        # update trade placed subscribers
        for func, fn_kwargs in self._new_trade_subscribers:
            func(trade, **fn_kwargs)

        return True, new_trade

    def cancel_trade(self, trade: Trade):
        # TODO: test
        cancelled_status = TradeStatus(
            state=TradeState.CANCELLED,
            filled=trade.status.filled,
            remaining=trade.status.remaining,
            ave_fill_price=trade.status.ave_fill_price,
            order_id=trade.status.order_id,
        )
        new_trade = Trade(
            contract=trade.contract,
            order=trade.order,
            status=cancelled_status,
        )
        trade_idx = self._placed_trades.index(trade)
        self._placed_trades[trade_idx] = new_trade

        self._update_trade_updates_subscribers(trade=trade)

    def get_position(
        self,
        contract: AContract,
        *args,
        account: Optional[str] = None,
        **kwargs,
    ) -> float:
        if account is not None:
            position = self._get_position_for_account(
                account=account, contract=contract,
            )
        else:
            position = self._get_cumulative_position(contract=contract)

        return position

    def get_transaction_fee(self) -> float:
        return self._abs_fee

    # ------------------------- Sim Methods ------------------------------------

    def step(self, cache_only: bool = True):
        while len(self._scheduled_trade_executions) != 0:
            trade, price, n_shares = self._scheduled_trade_executions.pop(0)
            self._execute_trade(
                trade=trade, price=price, n_shares=n_shares,
            )

    def simulate_trade_execution(
        self,
        trade: Trade,
        price: Optional[float] = None,
        n_shares: Optional[float] = None,
    ):
        # TODO: test
        # TODO: implement for Limit and Stop Loss Orders
        self._scheduled_trade_executions.append((trade, price, n_shares),)

    # -------------------------- Helpers ---------------------------------------

    def _get_increment_valid_id(self) -> int:
        valid_id = self._valid_id
        self._valid_id += 1
        return valid_id

    def _execute_trade(
        self,
        trade: Trade,
        price: Optional[float] = None,
        n_shares: Optional[float] = None,
    ):

        trade_idx = self._placed_trades.index(trade)
        trade = self._placed_trades[trade_idx]

        self._validate_trade_execution(
            trade=trade, price=price, n_shares=n_shares,
        )

        contract = trade.contract
        order = trade.order
        filled = trade.status.filled

        if n_shares is None:
            n_shares = order.quantity - filled

        if price is None:
            price = self._get_current_price(contract=contract)

        if order.action == OrderAction.BUY:
            funds_delta = -(n_shares * price + self.get_transaction_fee())
            shares_delta = n_shares
        else:
            funds_delta = n_shares * price + self.get_transaction_fee()
            shares_delta = -n_shares
        self.acc_cash[contract.currency] += funds_delta
        self._add_to_position(
            contract=contract, n_shares=shares_delta, fill_price=price,
        )

        filled = trade.status.filled
        new_filled = filled + n_shares
        ave_price = trade.status.ave_fill_price
        new_ave_price = (ave_price * filled + price * n_shares) / new_filled
        new_status = TradeStatus(
            state=TradeState.FILLED,
            filled=new_filled,
            remaining=order.quantity - new_filled,
            ave_fill_price=new_ave_price,
            order_id=order.order_id,
        )
        trade.status = new_status
        self._update_trade_updates_subscribers(trade=trade)

    @staticmethod
    def _validate_trade_execution(
        trade: Trade,
        price: Optional[float] = None,
        n_shares: Optional[float] = None,
    ):
        # TODO: test
        order = trade.order
        filled = trade.status.filled

        if n_shares is not None and n_shares > order.quantity - filled:
            raise ValueError(
                f"Cannot simulate filling more shares ({n_shares}) than the"
                f" order's remaining unfilled ({order.quantity - filled})."
            )

        if isinstance(order, LimitOrder):
            legal = True
            if order.action == OrderAction.BUY and price > order.limit_price:
                legal = False
            elif (
                order.action == OrderAction.SELL and price < order.limit_price
            ):
                legal = False

            if not legal:
                raise ValueError(
                    f"Cannot simulate filling a limit {order.action.value}"
                    f" order with limit price {order.limit_price} at"
                    f" the simulation price of {price}."
                )

    def _add_to_position(
        self,
        contract: AContract,
        n_shares: float,
        fill_price: float,
        account: str = DEFAULT_SIM_ACC,
    ):
        acc_positions = self._positions.setdefault(account, {})

        if contract not in acc_positions:
            new_position_size = n_shares
            new_ave_fill_price = fill_price
        else:
            curr_pos = acc_positions[contract]
            new_position_size = curr_pos.position + n_shares
            prev_price = curr_pos.position * curr_pos.ave_fill_price
            curr_price = n_shares * fill_price
            if new_position_size != 0:
                new_ave_fill_price = (
                    prev_price + curr_price
                ) / new_position_size
            else:
                new_ave_fill_price = 0

        new_position = Position(
            account=account,
            contract=contract,
            position=new_position_size,
            ave_fill_price=new_ave_fill_price,
        )
        acc_positions[contract] = new_position
        self._update_position_updates_subscribers(position=new_position)

    def _get_position_for_account(
        self, account: str, contract: AContract,
    ) -> float:
        position = self._positions[account][contract].position
        return position

    def _get_cumulative_position(self, contract: AContract) -> float:
        position = 0

        for acc_dict in self._positions.values():
            con_pos = acc_dict.get(contract)
            if con_pos is not None:
                position += con_pos.position

        return position

    def _update_trade_updates_subscribers(self, trade: Trade):
        trade_idx = self._placed_trades.index(trade)
        trade = self._placed_trades[trade_idx]
        status = trade.status

        for func, fn_kwargs in self._trade_updates_subscribers:
            func(trade, status, **fn_kwargs)

    def _update_position_updates_subscribers(self, position: Position):
        for func, fn_kwargs in self._position_updates_subscribers:
            func(position, **fn_kwargs)

    def _get_current_price(self, contract: AContract) -> float:
        # TODO: use 1s aggregation of ticks, if available
        bar = self._streamer.get_bar(
            contract=contract, bar_size=self.sim_clock.time_step,
        )
        price = bar["open"]
        return price
