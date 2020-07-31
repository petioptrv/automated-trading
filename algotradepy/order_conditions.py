from abc import ABC
from datetime import datetime as dt
from enum import Enum

from algotradepy.contracts import Exchange, AContract


class PriceTriggerMethod(Enum):
    MID_POINT = 8


class ConditionDirection(Enum):
    MORE = True
    LESS = False


class ChainType(Enum):
    OR = 0
    AND = 1


class ACondition(ABC):
    def __init__(self, chain_type: ChainType = ChainType.AND):
        super().__init__()
        self._chain_type = chain_type

    @property
    def chain_type(self) -> ChainType:
        return self._chain_type


class PriceCondition(ACondition):
    def __init__(
        self,
        contract: AContract,
        price: float,
        trigger_method: PriceTriggerMethod,
        price_direction: ConditionDirection,
        chain_type: ChainType = ChainType.AND,
    ):
        super().__init__(chain_type=chain_type)
        self._contract = contract
        self._price = price
        self._trigger_method = trigger_method
        self._price_direction = price_direction

    @property
    def contract(self) -> AContract:
        return self._contract

    @property
    def price(self):
        return self._price

    @property
    def trigger_method(self) -> PriceTriggerMethod:
        return self._trigger_method

    @property
    def price_direction(self) -> ConditionDirection:
        return self._price_direction


class DateTimeCondition(ACondition):
    def __init__(
        self,
        target_datetime: dt,
        time_direction: ConditionDirection,
        chain_type: ChainType = ChainType.AND,
    ):
        super().__init__(chain_type=chain_type)
        self._target_datetime = target_datetime
        self._time_direction = time_direction

    @property
    def target_datetime(self) -> dt:
        return self._target_datetime

    @property
    def time_direction(self) -> ConditionDirection:
        return self._time_direction


class ExecutionCondition(ACondition):
    def __init__(
        self,
        contract_type: type(AContract),
        exchange: Exchange,
        symbol: str,
        chain_type: ChainType = ChainType.AND,
    ):
        super().__init__(chain_type=chain_type)
        self._contract_type = contract_type
        self._exchange = exchange
        self._symbol = symbol

    @property
    def contract_type(self) -> type(AContract):
        return self._contract_type

    @property
    def exchange(self) -> Exchange:
        return self._exchange

    @property
    def symbol(self) -> str:
        return self._symbol
