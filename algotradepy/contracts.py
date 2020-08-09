from abc import ABC
from datetime import date
from enum import Enum
from typing import Optional

from algotradepy.utils import ReprAble, Comparable


class PriceType(Enum):
    """The price type.

    Used when requesting price updates for a given contract.

    Values
    ------
    * MARKET
    * ASK
    * BID
    """

    MARKET = "MARKET"
    ASK = "ASK"
    BID = "BID"


class Exchange(Enum):
    """The available exchanges.

    Values
    ------
    * Automatic

        * SMART

    * North America

        * NYSE
        * NASDAQ
        * AMEX
        * ARCA
        * TSE

    * Europe

        * FWB
        * IBIS
        * VSE
        * LSE
        * BATEUK
        * ENEXT_BE
        * SBF
        * AEB

    * Asia/Pacific

        * SEHK
        * ASX
        * TSEJ

    * Global

        * FOREX
    """

    SMART = "SMART"

    # North America
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"  # IB's ISLAND
    AMEX = "AMEX"
    ARCA = "ARCA"
    TSE = "TSE"
    VENTURE = "VENTURE"

    # Europe
    FWB = "FWB"
    IBIS = "IBIS"
    VSE = "VSE"
    LSE = "LSE"
    BATEUK = "BATEUK"
    ENEXT_BE = "ENEXT.BE"
    SBF = "SBF"
    AEB = "AEB"

    # Asia/Pacific
    SEHK = "SEHK"
    ASX = "ASX"
    TSEJ = "TSEJ"

    # Global
    FOREX = "FOREX"


class Currency(Enum):
    """The available currencies.

    Values
    ------
    * North America

        * USD
        * CAD

    * Europe

        * EUR
        * GBP

    * Asia/Pacific

        * AUD
        * HKD
        * JPY
    """

    # North America
    USD = "USD"
    CAD = "CAD"

    # Europe
    EUR = "EUR"
    GBP = "GBP"

    # Asia/Pacific
    AUD = "AUD"
    HKD = "HKD"
    JPY = "JPY"


class Right(Enum):
    """Option right.

    Values
    ------
    * CALL
    * PUT
    """

    CALL = "CALL"
    PUT = "PUT"


class AContract(ABC, ReprAble, Comparable):
    """The abstract contract class defining the basic contract properties.

    Parameters
    ----------
    symbol : str
        The symbol for the contract.
    con_id : int, optional, default None
        The contract ID.
    exchange : ~algotradepy.contracts.Exchange, default `Exchange.SMART`
        The exchange on which this contract is traded.
    currency : ~algotradepy.contracts.Currency, default `Currency.USD`
        The currency of the contract.
    """

    def __init__(
        self,
        symbol: str,
        con_id: Optional[int] = None,
        exchange: Exchange = Exchange.SMART,
        currency: Currency = Currency.USD,
    ):
        super().__init__()
        self._con_id = con_id
        self._symbol = symbol
        self._exchange = exchange
        self._currency = currency

    @property
    def con_id(self) -> Optional[int]:
        return self._con_id

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def exchange(self) -> Optional[Exchange]:
        return self._exchange

    @exchange.setter
    def exchange(self, ex: Exchange):
        assert isinstance(ex, Exchange)
        self._exchange = ex

    @property
    def currency(self) -> Currency:
        return self._currency

    @currency.setter
    def currency(self, cu: Currency):
        assert isinstance(cu, Currency)
        self._currency = cu


class StockContract(AContract):
    """Defines a stock contract.

    Parameters
    ----------
    symbol
    con_id
    exchange
    currency
    """

    def __init__(
        self,
        symbol: str,
        con_id: Optional[int] = None,
        exchange: Optional[Exchange] = None,
        currency: Currency = Currency.USD,
    ):
        super().__init__(
            con_id=con_id, symbol=symbol, exchange=exchange, currency=currency,
        )


class OptionContract(AContract):
    """Defines an option contract.

    Parameters
    ----------
    symbol
    strike : float
        The option's strike price.
    right : ~algotradepy.contracts.Right
        The option's right.
    multiplier : float
        The option's multiplier.
    last_trade_date : datetime.date
        The option contract's expiration date.
    con_id
    exchange
    currency
    """

    # TODO: test; todo after getting option chain...
    def __init__(
        self,
        symbol: str,
        strike: float,
        right: Right,
        multiplier: float,
        last_trade_date: date,
        con_id: Optional[int] = None,
        exchange: Optional[Exchange] = None,
        currency: Currency = Currency.USD,
    ):
        super().__init__(
            con_id=con_id, symbol=symbol, exchange=exchange, currency=currency
        )
        self._strike = strike
        self._right = right
        self._multiplier = multiplier
        self._last_trade_date = last_trade_date

    @property
    def strike(self) -> float:
        return self._strike

    @property
    def right(self) -> Right:
        return self._right

    @property
    def multiplier(self) -> float:
        return self._multiplier

    @property
    def last_trade_date(self) -> date:
        return self._last_trade_date


class ForexContract(AContract):
    def __init__(
        self,
        symbol: str,
        con_id: Optional[int] = None,
        exchange: Optional[Exchange] = Exchange.FOREX,
        currency: Currency = Currency.USD,
    ):
        super().__init__(
            con_id=con_id, symbol=symbol, exchange=exchange, currency=currency
        )


def are_loosely_equal_contracts(
    loose: AContract, well_defined: AContract,
) -> bool:
    """Used to compare a loosely- and a well-defined contract.

    This method is useful for tasks such as getting all positions for a given
    stock symbol, irrespective of the exchange.

    Parameters
    ----------
    loose : AContract
        The loosely-defined contract.
    well_defined : AContract
        The more strictly-defined contract.
    """
    if loose == well_defined:
        equal = True
    else:
        if not isinstance(loose, type(well_defined)):
            equal = False
        else:
            if isinstance(loose, StockContract):
                equal = _are_loosely_equal_stock(
                    loose=loose, well_defined=well_defined,
                )
            elif isinstance(loose, OptionContract):
                equal = _are_loosely_equal_option(
                    loose=loose, well_defined=well_defined,
                )
            elif isinstance(loose, ForexContract):
                equal = _are_loosely_equal_forex(
                    loose=loose, well_defined=well_defined,
                )
            else:
                raise TypeError(f"Unrecognized contract type {type(loose)}.")

    return equal


def _are_loosely_equal_stock(
    loose: StockContract, well_defined: StockContract,
) -> bool:
    equal = _are_loosely_equal_a_contract(
        loose=loose, well_defined=well_defined,
    )
    return equal


def _are_loosely_equal_option(
    loose: OptionContract, well_defined: OptionContract,
) -> bool:
    equal = True
    a_comparison = _are_loosely_equal_a_contract(
        loose=loose, well_defined=well_defined,
    )

    if not a_comparison:
        equal = False
    elif loose.strike != well_defined.strike:
        equal = False
    elif loose.right != well_defined.right:
        equal = False
    elif loose.multiplier != well_defined.multiplier:
        equal = False
    elif loose.last_trade_date != well_defined.last_trade_date:
        equal = False

    return equal


def _are_loosely_equal_forex(
    loose: ForexContract, well_defined: ForexContract,
) -> bool:
    equal = _are_loosely_equal_a_contract(
        loose=loose, well_defined=well_defined,
    )
    return equal


def _are_loosely_equal_a_contract(
    loose: AContract, well_defined: AContract,
) -> bool:
    equal = True

    if loose.symbol != well_defined.symbol:
        equal = False
    elif loose.con_id is not None and loose.con_id != well_defined.con_id:
        equal = False
    elif (
        loose.exchange is not None and loose.exchange != well_defined.exchange
    ):
        equal = False
    elif (
        loose.currency is not None and loose.currency != well_defined.currency
    ):
        equal = False

    return equal
