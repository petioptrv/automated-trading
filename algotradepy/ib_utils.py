import calendar
from datetime import date, datetime, timedelta
from typing import Optional, Type
import logging

from algotradepy.position import Position

try:
    import ib_insync
except ImportError:
    raise ImportError(
        "Optional package ib_insync not install. Please install"
        " using 'pip install ib_insync'."
    )
from ib_insync.util import UNSET_DOUBLE
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
from ib_insync import Position as _IBPosition

from algotradepy.connectors.ib_connector import (
    IBConnector,
    build_and_start_connector,
    SERVER_BUFFER_TIME,
)
from algotradepy.contracts import (
    AContract,
    StockContract,
    OptionContract,
    Exchange,
    Right,
    ForexContract,
    Currency,
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
from algotradepy.time_utils import is_time_aware

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


class IBBase:
    def __init__(
        self,
        simulation: bool = True,
        ib_connector: Optional[IBConnector] = None,
    ):
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

    def __del__(self):
        if hasattr(self, "_ib_conn"):
            self._ib_conn.disconnect()

    def sleep(self, secs: float = SERVER_BUFFER_TIME):
        self._ib_conn.sleep(secs)

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
        # TODO: test
        if not isinstance(ib_order, _IBOrder):
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
        elif (
            isinstance(ib_order, _IBLimitOrder) or ib_order.orderType == "LMT"
        ):
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
                action=order.action.value, totalQuantity=order.quantity,
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
        conjunction = "a" if condition.chain_type == ChainType.AND else "o"
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
        conjunction = "a" if condition.chain_type == ChainType.AND else "o"
        is_more = condition.time_direction == ConditionDirection.MORE
        dt = condition.target_datetime
        dt_format = _IB_DATETIME_FORMAT
        if is_time_aware(dt):
            dt_format = _IB_DATETIME_FORMAT_TZ
        ib_datetime_str = dt.strftime(dt_format)
        ib_datetime_str = self._validate_ib_dt_str(ib_dt_str=ib_datetime_str)
        ib_cond = _IBTimeCondition(
            conjunction=conjunction, isMore=is_more, time=ib_datetime_str,
        )

        return ib_cond

    @staticmethod
    def _validate_ib_dt_str(ib_dt_str: str) -> str:
        if ib_dt_str[-4:] == "CEST":
            ib_dt_str = ib_dt_str[:-4] + "CET"

        return ib_dt_str

    def _to_ib_execution_condition(
        self, condition: ExecutionCondition,
    ) -> _IBExecutionCondition:
        conjunction = "a" if condition.chain_type == ChainType.AND else "o"
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
        currency = Currency.__getattr__(ib_currency)
        return currency

    @staticmethod
    def _to_ib_currency(currency: Currency) -> str:
        ib_currency = currency.value
        return ib_currency

    def _from_ib_position(self, ib_position: _IBPosition) -> Position:
        contract = self._from_ib_contract(ib_contract=ib_position.contract)
        pos = Position(
            contract=contract,
            position=ib_position.position,
            ave_fill_price=ib_position.avgCost,
        )
        return pos

    def _to_ib_bar_size(self, bar_size: timedelta) -> str:
        self._validate_bar_size(bar_size=bar_size)

        if bar_size == timedelta(seconds=1):
            bar_size_str = "1 secs"
        elif bar_size < timedelta(minutes=1):
            bar_size_str = f"{bar_size.seconds} secs"
        elif bar_size == timedelta(minutes=1):
            bar_size_str = "1 min"
        elif bar_size < timedelta(hours=1):
            bar_size_str = f"{bar_size.seconds // 60} mins"
        elif bar_size == timedelta(hours=1):
            bar_size_str = "1 hour"
        elif bar_size < timedelta(days=1):
            bar_size_str = f"{bar_size.seconds // 60 // 60} hours"
        elif bar_size == timedelta(days=1):
            bar_size_str = "1 day"
        else:
            raise ValueError(f"Unsupported bar size {bar_size}.")

        return bar_size_str

    @staticmethod
    def _validate_bar_size(bar_size: timedelta):
        valid_sizes = [
            timedelta(seconds=1),
            timedelta(seconds=5),
            timedelta(seconds=10),
            timedelta(seconds=15),
            timedelta(seconds=30),
            timedelta(minutes=1),
            timedelta(minutes=2),
            timedelta(minutes=3),
            timedelta(minutes=5),
            timedelta(minutes=15),
            timedelta(minutes=20),
            timedelta(minutes=30),
            timedelta(hours=1),
            timedelta(hours=2),
            timedelta(hours=3),
            timedelta(hours=4),
            timedelta(hours=8),
            timedelta(days=1),
            timedelta(weeks=1),
            timedelta(days=30),
        ]

        if bar_size not in valid_sizes:
            raise ValueError(
                f"Got invalid bar size {bar_size}."
                f" Valid bar sizes are {valid_sizes}."
            )
