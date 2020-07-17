import calendar
from datetime import datetime, date, timedelta
from typing import Optional, Callable, Tuple, Dict, List, Type
import logging

try:
    import ib_insync
except ImportError:
    raise ImportError(
        f"Optional package ib_insync not install. Please install"
        f" using 'pip install ib_insync'."
    )
from ib_insync.util import UNSET_DOUBLE
from ibapi.account_summary_tags import AccountSummaryTags as _AccountSummaryTags
from ib_insync.contract import (
    Contract as _IBContract,
    Stock as _IBStock,
    Option as _IBOption,
    Forex as _IBForex,
)
from ib_insync.order import (
    Trade as _IBTrade,
    Order as _IBOrder,
    MarketOrder as _IBMarketOrder,
    LimitOrder as _IBLimitOrder,
    OrderStatus as _IBOrderStatus,
    PriceCondition as _IBPriceCondition,
    TimeCondition as _IBTimeCondition,
    ExecutionCondition as _IBExecutionCondition,
)
from ib_insync.ticker import Ticker as _IBTicker

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
    ForexContract,
    Currency, are_loosely_equal_contracts,
)
from algotradepy.order_conditions import (
    ACondition,
    PriceCondition,
    ChainType,
    ConditionDirection,
    PriceTriggerMethod,
    DateTimeCondition,
    ExecutionCondition,
)
from algotradepy.orders import (
    MarketOrder,
    AnOrder,
    LimitOrder,
    OrderAction,
    TrailingStopOrder,
)
from algotradepy.trade import Trade, TradeState, TradeStatus

_IB_FULL_DATE_FORMAT = "%Y%m%d"
_IB_MONTH_DATE_FORMAT = "%Y%m"
_IB_DATETIME_FORMAT = f"{_IB_FULL_DATE_FORMAT} %H:%M:%S"
_IB_DATETIME_FORMAT_TZ = f"{_IB_DATETIME_FORMAT} %Z"


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

        # {contract: {func: price_type}}
        self._price_subscriptions: Optional[Dict] = None
        self._market_data_type_set = False

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
            self._from_ib_trade(ib_trade=ib_trade)
            for ib_trade in ib_trades
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

    def sleep(self, secs: float = SERVER_BUFFER_TIME):
        self._ib_conn.sleep(secs)

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

    def subscribe_to_bars(
            self,
            contract: AContract,
            bar_size: timedelta,
            func: Callable,
            fn_kwargs: Optional[dict] = None,
    ):
        # TODO: implement
        raise NotImplementedError

    def subscribe_to_tick_data(
            self,
            contract: AContract,
            func: Callable,
            fn_kwargs: Optional[Dict] = None,
            price_type: PriceType = PriceType.MARKET,
    ):
        if fn_kwargs is None:
            fn_kwargs = {}

        self._set_market_data_type()

        def price_update(ticker: _IBTicker):
            contract_ = self._from_ib_contract(ib_contract=ticker.contract)
            assert contract_ in self._price_subscriptions

            con_subs_ = self._price_subscriptions[contract_]

            for func_, price_type_ in con_subs_.items():
                if price_type_ == PriceType.MARKET:
                    price_ = ticker.midpoint()
                elif price_type_ == PriceType.ASK:
                    price_ = ticker.ask
                elif price_type_ == PriceType.BID:
                    price_ = ticker.bid
                else:
                    raise TypeError(f"Unknown price type {price_type_}.")

                func_(contract_, price_, **fn_kwargs)

        previously_requested = contract in self._price_subscriptions

        con_subs = self._price_subscriptions.setdefault(contract, {})
        con_subs[func] = price_type

        if not previously_requested:
            ib_contract = self._to_ib_contract(contract=contract)
            tick = self._ib_conn.reqMktData(
                contract=ib_contract,
                genericTickList="",
                snapshot=False,
                regulatorySnapshot=False,
                mktDataOptions=[],
            )
            tick.updateEvent += price_update

    def cancel_tick_data(self, contract: AContract, func: Callable):
        if self._market_data_type_set is None:
            raise RuntimeError("No price subscriptions were requested.")

        found = False
        for sub_contract, sub_dict in self._price_subscriptions.items():
            if contract == sub_contract and func in sub_dict:
                found = True
                del sub_dict[func]
                if len(sub_dict) == 0:
                    self._cancel_price_subscription(contract=contract)
                break

        if not found:
            raise ValueError(
                f"No price subscription found for contract {contract} and"
                f" function {func}."
            )

    def place_trade(
            self,
            trade: Trade,
            *args,
            await_confirm: bool = False,
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
            self.sleep()

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
            pos_contract = self._from_ib_contract(ib_contract=position.contract)
            if are_loosely_equal_contracts(
                    loose=contract, well_defined=pos_contract,
            ):
                pos = position.position
                break

        return pos

    def get_transaction_fee(self) -> float:
        # TODO: implement
        # TODO: test
        raise NotImplementedError

    # ---------------------- Market Data Helpers -------------------------------

    def _set_market_data_type(self):
        if not self._market_data_type_set:
            self._ib_conn.reqMarketDataType(marketDataType=4)
            self._market_data_type_set = True
            self._price_subscriptions = {}

    def _cancel_all_price_subscriptions(self):
        if self._price_subscriptions is not None:
            sub_contracts = list(self._price_subscriptions.keys())
            for sub_contract in sub_contracts:
                self._cancel_price_subscription(contract=sub_contract)

    def _cancel_price_subscription(self, contract: AContract):
        ib_contract = self._to_ib_contract(contract=contract)
        self._ib_conn.cancelMktData(contract=ib_contract)
        del self._price_subscriptions[contract]

    # ------------------------------ Converters --------------------------------

    def _from_ib_trade(self, ib_trade: _IBTrade) -> Trade:
        contract = self._from_ib_contract(ib_contract=ib_trade.contract)
        order = self._from_ib_order(ib_order=ib_trade.order)
        status = self._from_ib_status(ib_order_status=ib_trade.orderStatus)
        trade = Trade(contract=contract, order=order, status=status)

        return trade

    def _from_ib_contract(self, ib_contract: _IBContract):
        contract = None

        exchange = self._from_ib_exchange(ib_exchange=ib_contract.exchange)
        currency = self._from_ib_currency(ib_currency=ib_contract.currency)
        con_id = ib_contract.conId
        if con_id == 0:
            con_id = None

        if isinstance(ib_contract, _IBStock):
            contract = StockContract(
                con_id=con_id,
                symbol=ib_contract.symbol,
                exchange=exchange,
                currency=currency,
            )
        elif isinstance(ib_contract, _IBOption):
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
                con_id=con_id,
                symbol=ib_contract.symbol,
                strike=ib_contract.strike,
                right=right,
                multiplier=float(ib_contract.multiplier),
                last_trade_date=last_trade_date,
                exchange=exchange,
                currency=currency,
            )
        elif isinstance(ib_contract, _IBForex):
            contract = ForexContract(
                symbol=ib_contract.symbol,
                con_id=con_id,
                exchange=exchange,
                currency=currency,
            )
        else:
            logging.warning(
                f"Contract type {ib_contract.secType} not understood."
                f" No contract was built."
            )

        return contract

    def _to_ib_contract(self, contract: AContract) -> _IBContract:
        ib_exchange = self._to_ib_exchange(exchange=contract.exchange)
        ib_currency = self._to_ib_currency(currency=contract.currency)

        if isinstance(contract, StockContract):
            ib_contract = _IBStock(
                symbol=contract.symbol,
                exchange=ib_exchange,
                currency=ib_currency,
            )
        elif isinstance(contract, OptionContract):
            ib_last_trade_date = contract.last_trade_date.strftime(
                _IB_FULL_DATE_FORMAT,
            )
            if contract.right == Right.CALL:
                ib_right = "C"
            else:
                ib_right = "P"
            ib_contract = _IBOption(
                symbol=contract.symbol,
                lastTradeDateOrContractMonth=ib_last_trade_date,
                strike=contract.strike,
                right=ib_right,
                exchange=ib_exchange,
                multiplier=str(contract.multiplier),
                currency=ib_currency,
            )
        elif isinstance(contract, ForexContract):
            ib_contract = _IBForex(
                pair=f"{contract.symbol}{ib_currency}",
                exchange=ib_exchange,
                symbol=contract.symbol,
                currency=ib_currency,
            )
        else:
            raise TypeError(f"Unknown type of contract {type(contract)}.")

        return ib_contract

    @staticmethod
    def _from_ib_order(ib_order: _IBOrder) -> Optional[AnOrder]:
        if isinstance(ib_order, _IBOrder):
            logging.warning(
                f"Received poorly defined order from IB: {ib_order}."
            )

        order = None
        if ib_order.action == "BUY":
            order_action = OrderAction.BUY
        else:
            order_action = OrderAction.SELL
        parent_id = ib_order.parentId if ib_order.parentId else None

        if isinstance(ib_order, _IBMarketOrder) or ib_order.orderType == "MKT":
            order = MarketOrder(
                order_id=ib_order.orderId,
                action=order_action,
                quantity=ib_order.totalQuantity,
                parent_id=parent_id,
            )
        elif isinstance(ib_order, _IBLimitOrder) or ib_order.orderType == "LMT":
            order = LimitOrder(
                order_id=ib_order.orderId,
                action=order_action,
                quantity=ib_order.totalQuantity,
                limit_price=ib_order.lmtPrice,
                parent_id=parent_id,
            )
        elif ib_order.orderType == "TRAIL":
            aux_price = ib_order.auxPrice
            if aux_price == UNSET_DOUBLE:
                aux_price = None
            trail_stop_price = ib_order.trailStopPrice
            if trail_stop_price == UNSET_DOUBLE:
                trail_stop_price = None
            trail_percent = ib_order.trailingPercent
            if trail_percent == UNSET_DOUBLE:
                trail_percent = None
            order = TrailingStopOrder(
                order_id=ib_order.orderId,
                action=order_action,
                quantity=ib_order.totalQuantity,
                trail_stop_price=trail_stop_price,
                aux_price=aux_price,
                trail_percent=trail_percent,
                parent_id=parent_id,
            )
        else:
            logging.warning(
                f"Order type {ib_order.orderType} not understood."
                f" No order was built."
            )

        return order

    def _to_ib_order(self, order: AnOrder) -> _IBOrder:
        if isinstance(order, MarketOrder):
            ib_order = _IBMarketOrder(
                action=order.action.value,
                totalQuantity=order.quantity,
            )
        elif isinstance(order, LimitOrder):
            ib_order = _IBLimitOrder(
                action=order.action.value,
                totalQuantity=order.quantity,
                lmtPrice=round(order.limit_price, 2),
            )
        elif isinstance(order, TrailingStopOrder):
            ib_trail_percent = order.trail_percent or UNSET_DOUBLE
            ib_stop_price = order.trail_stop_price or UNSET_DOUBLE
            ib_aux_price = order.aux_price or UNSET_DOUBLE
            ib_order = _IBOrder(
                orderType="TRAIL",
                action=order.action.value,
                totalQuantity=order.quantity,
                trailingPercent=ib_trail_percent,
                trailStopPrice=ib_stop_price,
                auxPrice=ib_aux_price,
            )
        else:
            raise TypeError(f"Unknown type of order {type(order)}.")

        if order.time_in_force is not None:
            ib_tif = order.time_in_force.value
        else:
            ib_tif = ""
        ib_order.tif = ib_tif

        if order.parent_id is not None:
            ib_order.parentId = order.parent_id

        for cond in order.conditions:
            ib_cond = self._to_ib_condition(condition=cond)
            ib_order.conditions.append(ib_cond)

        return ib_order

    def _to_ib_condition(self, condition: ACondition):
        if isinstance(condition, PriceCondition):
            ib_cond = self._to_ib_price_condition(condition=condition)
        elif isinstance(condition, DateTimeCondition):
            ib_cond = self._to_ib_time_condition(condition=condition)
        elif isinstance(condition, ExecutionCondition):
            ib_cond = self._to_ib_execution_condition(condition=condition)
        else:
            raise TypeError(
                f"Unrecognized order condition type {type(condition)}."
            )

        return ib_cond

    def _to_ib_price_condition(
            self, condition: PriceCondition,
    ) -> _IBPriceCondition:
        conjunction = 'a' if condition.chain_type == ChainType.AND else 'o'
        ib_contract = self._to_ib_contract(contract=condition.contract)
        con_detail_defs = self._ib_conn.reqContractDetails(
            contract=ib_contract,
        )
        if len(con_detail_defs) == 0:
            raise ValueError(
                f"Received an unrecognized contract definition"
                f" {condition.contract}."
            )
        elif len(con_detail_defs) != 1:
            raise ValueError(
                f"Received an ambiguous contract definition"
                f" {condition.contract}."
            )
        con_def = con_detail_defs[0].contract
        is_more = condition.price_direction == ConditionDirection.MORE
        ib_trigger_method = self._to_ib_trigger_method(
            trigger_method=condition.trigger_method,
        )
        ib_cond = _IBPriceCondition(
            conjunction=conjunction,
            isMore=is_more,
            price=condition.price,
            conId=con_def.conId,
            exch=con_def.exchange,
            triggerMethod=ib_trigger_method,
        )

        return ib_cond

    def _to_ib_time_condition(
            self, condition: DateTimeCondition,
    ) -> _IBTimeCondition:
        conjunction = 'a' if condition.chain_type == ChainType.AND else 'o'
        is_more = condition.time_direction == ConditionDirection.MORE
        dt = condition.target_datetime
        dt_format = _IB_DATETIME_FORMAT
        # TODO: move to is_time_aware util function
        if dt.tzinfo is not None or dt.tzinfo.utcoffset(dt) is not None:
            dt_format = _IB_DATETIME_FORMAT_TZ
        ib_datetime_str = dt.strftime(dt_format)
        ib_datetime_str = self._validate_ib_dt_str(ib_dt_str=ib_datetime_str)
        ib_cond = _IBTimeCondition(
            conjunction=conjunction,
            isMore=is_more,
            time=ib_datetime_str,
        )

        return ib_cond

    @staticmethod
    def _validate_ib_dt_str(ib_dt_str: str) -> str:
        if ib_dt_str[-4:] == "CEST":
            ib_dt_str = ib_dt_str[:-4] + "CET"

        return ib_dt_str

    def _to_ib_execution_condition(
            self,
            condition: ExecutionCondition,
    ) -> _IBExecutionCondition:
        conjunction = 'a' if condition.chain_type == ChainType.AND else 'o'
        ib_sec_type = self._to_ib_sec_type(
            contract_type=condition.contract_type,
        )
        ib_exchange = self._to_ib_exchange(exchange=condition.exchange)
        ib_cond = _IBExecutionCondition(
            conjunction=conjunction,
            secType=ib_sec_type,
            exch=ib_exchange,
            symbol=condition.symbol,
        )

        return ib_cond

    @staticmethod
    def _to_ib_trigger_method(trigger_method: PriceTriggerMethod) -> int:
        ib_trigger_method = trigger_method.value
        return ib_trigger_method

    @staticmethod
    def _to_ib_sec_type(contract_type: Type) -> str:
        if contract_type == StockContract:
            ib_sec_type = "STK"
        elif contract_type == OptionContract:
            ib_sec_type = "OPT"
        elif contract_type == ForexContract:
            ib_sec_type = "CASH"
        else:
            raise ValueError(f"Unrecognized contract type {contract_type}.")

        return ib_sec_type

    def _from_ib_status(self, ib_order_status: _IBOrderStatus) -> TradeStatus:
        state = self._from_ib_state(ib_state=ib_order_status.status)
        status = TradeStatus(
            state=state,
            filled=ib_order_status.filled,
            remaining=ib_order_status.remaining,
            ave_fill_price=ib_order_status.avgFillPrice,
            order_id=ib_order_status.orderId,
        )

        return status

    @staticmethod
    def _from_ib_state(ib_state: str) -> TradeState:
        if ib_state == "ApiPending":
            state = TradeState.PENDING
        elif ib_state == "PendingSubmit":
            state = TradeState.PENDING
        elif ib_state == "PreSubmitted":
            state = TradeState.SUBMITTED
        elif ib_state == "Submitted":
            state = TradeState.SUBMITTED
        elif ib_state == "ApiCancelled":
            state = TradeState.CANCELLED
        elif ib_state == "Cancelled":
            state = TradeState.CANCELLED
        elif ib_state == "Filled":
            state = TradeState.FILLED
        elif ib_state == "Inactive":
            state = TradeState.INACTIVE
        else:
            raise ValueError(f"Unknown IB order status {ib_state}.")

        return state

    @staticmethod
    def _from_ib_exchange(ib_exchange: str) -> Exchange:
        # TODO: test
        if ib_exchange in ["", "SMART"]:
            exchange = None
        elif ib_exchange == "ISLAND":
            exchange = Exchange.NASDAQ
        elif ib_exchange == "ENEXT.BE":
            exchange = Exchange.ENEXT_BE
        elif ib_exchange == "IDEALPRO":
            exchange = Exchange.FOREX
        else:
            exchange = Exchange.__getattr__(ib_exchange)

        return exchange

    @staticmethod
    def _to_ib_exchange(exchange: Exchange) -> str:
        # TODO: test
        if exchange is None:
            ib_exchange = "SMART"
        elif exchange == Exchange.NASDAQ:
            ib_exchange = "ISLAND"
        elif exchange == Exchange.ENEXT_BE:
            ib_exchange = "ENEXT.BE"
        elif exchange == Exchange.FOREX:
            ib_exchange = "IDEALPRO"
        else:
            ib_exchange = exchange.value

        return ib_exchange

    @staticmethod
    def _from_ib_currency(ib_currency: str) -> Currency:
        # TODO: test
        currency = Currency.__getattr__(ib_currency)
        return currency

    @staticmethod
    def _to_ib_currency(currency: Currency) -> str:
        # TODO: test
        ib_currency = currency.value
        return ib_currency
