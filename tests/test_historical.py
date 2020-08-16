from datetime import date, timedelta
from typing import Optional

import pandas as pd
import numpy as np
import pytest

from algotradepy.contracts import StockContract
from algotradepy.historical.loaders import HistoricalRetriever
from algotradepy.historical.providers.yahoo_provider import (
    YahooHistoricalProvider,
)
from algotradepy.historical.transformers import HistoricalAggregator
from algotradepy.time_utils import generate_trading_days
from tests.conftest import (
    TEST_DATA_DIR,
    can_test_iex,
    can_test_polygon,
    get_token,
    can_test_ib,
)


def validate_data_range(
    data: pd.DataFrame,
    start_date: date,
    end_date: date,
    abs_tol: Optional[int] = 0,
    rel_tol: Optional[float] = 0,
):
    target_dates = set(
        generate_trading_days(start_date=start_date, end_date=end_date,)
    )
    received_dates = set(
        [dt.date() for dt in np.unique(data.index.to_pydatetime())]
    )

    if len(received_dates - target_dates) != 0:
        raise ValueError(
            f"Data has out-of-range dates: {received_dates - target_dates}."
        )

    if abs_tol:
        if len(target_dates - received_dates) > abs_tol:
            raise ValueError(
                f"Data has {len(target_dates - received_dates)} missing dates,"
                f" but abs_tol is {abs_tol}."
            )

    if rel_tol:
        ratio = len(target_dates - received_dates) / len(target_dates)
        if ratio > rel_tol:
            raise ValueError(
                f"Data has {ratio} of the requested dates, but rel_tol"
                f" is {rel_tol}."
            )


def test_retriever_cached_tick():
    start_date = date(2020, 6, 17)
    end_date = date(2020, 6, 19)

    retriever = HistoricalRetriever(hist_data_dir=TEST_DATA_DIR)
    contract = StockContract(symbol="SCHW")
    data = retriever.retrieve_bar_data(
        contract=contract,
        start_date=start_date,
        end_date=end_date,
        bar_size=timedelta(0),
        cache_only=True,
    )

    assert len(data) != 0

    validate_data_range(data=data, start_date=start_date, end_date=end_date)


def test_retriever_cached_daily():
    start_date = date(2020, 4, 1)
    end_date = date(2020, 4, 2)

    retriever = HistoricalRetriever(hist_data_dir=TEST_DATA_DIR)
    contract = StockContract(symbol="SPY")
    data = retriever.retrieve_bar_data(
        contract=contract,
        start_date=start_date,
        end_date=end_date,
        bar_size=timedelta(days=1),
        cache_only=True,
    )

    assert len(data) != 0

    validate_data_range(data=data, start_date=start_date, end_date=end_date)


def test_retrieve_cached_trades():
    start_date = date(2020, 6, 17)
    end_date = date(2020, 6, 19)

    retriever = HistoricalRetriever(hist_data_dir=TEST_DATA_DIR)

    contract = StockContract(symbol="SPY")
    data = retriever.retrieve_trades_data(
        contract=contract,
        start_date=start_date,
        end_date=end_date,
        cache_only=True,
    )

    assert len(data) != 0

    validate_data_range(data=data, start_date=start_date, end_date=end_date)


HIST_PROVIDERS = [YahooHistoricalProvider()]

if can_test_iex():
    from algotradepy.historical.providers.iex_provider import (
        IEXHistoricalProvider,
    )

    HIST_PROVIDERS.append(IEXHistoricalProvider(get_token(name="iex")))

if can_test_polygon():
    from algotradepy.historical.providers.polygon_provider import (
        PolygonHistoricalProvider,
    )

    HIST_PROVIDERS.append(PolygonHistoricalProvider(get_token(name="polygon")))

if can_test_ib():
    from algotradepy.historical.providers.ib_provider import (
        IBHistoricalProvider,
    )

    HIST_PROVIDERS.append(IBHistoricalProvider())


@pytest.mark.parametrize("provider", [provider for provider in HIST_PROVIDERS])
def test_retrieve_non_cached_daily(tmpdir, provider):
    start_date = date(2020, 4, 1)
    end_date = date(2020, 4, 2)

    retriever = HistoricalRetriever(provider=provider, hist_data_dir=tmpdir,)
    contract = StockContract(symbol="SPY")

    try:
        data = retriever.retrieve_bar_data(
            contract=contract,
            start_date=start_date,
            end_date=end_date,
            bar_size=timedelta(days=1),
        )
    except NotImplementedError:
        return

    validate_data_range(data=data, start_date=start_date, end_date=end_date)


@pytest.mark.parametrize("provider", [provider for provider in HIST_PROVIDERS])
def test_retrieve_non_cached_intraday(tmpdir, provider):
    start_date = date.today() - timedelta(days=7)
    end_date = date.today() - timedelta(days=1)

    retriever = HistoricalRetriever(provider=provider, hist_data_dir=tmpdir)
    contract = StockContract(symbol="SPY")

    try:
        data = retriever.retrieve_bar_data(
            contract=contract,
            start_date=start_date,
            end_date=end_date,
            bar_size=timedelta(minutes=1),
        )
    except NotImplementedError:
        return

    validate_data_range(data=data, start_date=start_date, end_date=end_date)
    assert (
        np.isclose(len(data), 5 * 6.5 * 60, atol=7 * 60)
        or len(data) == 4800  # for outside RTHs IB
    )


@pytest.mark.parametrize("provider", [provider for provider in HIST_PROVIDERS])
def test_retrieve_non_cached_trades_data(tmpdir, provider):
    start_date = date(2020, 7, 22)
    end_date = date(2020, 7, 23)

    retriever = HistoricalRetriever(provider=provider, hist_data_dir=tmpdir)
    contract = StockContract(symbol="SPY")

    try:
        data = retriever.retrieve_trades_data(
            contract=contract, start_date=start_date, end_date=end_date,
        )
    except NotImplementedError:
        return

    validate_data_range(data=data, start_date=start_date, end_date=end_date)


@pytest.mark.skipif(
    len(generate_trading_days(start_date=date.today(), end_date=date.today()))
    == 0,
    reason="Today is not a trading day.",
)
@pytest.mark.parametrize("provider", [provider for provider in HIST_PROVIDERS])
def test_retrieve_non_cached_trades_data_today_partial(tmpdir, provider):
    end_date = date.today()
    start_date = end_date - timedelta(days=1)

    retriever = HistoricalRetriever(provider=provider, hist_data_dir=tmpdir)
    contract = StockContract(symbol="SPY")

    try:
        data = retriever.retrieve_trades_data(
            contract=contract,
            start_date=start_date,
            end_date=end_date,
            allow_partial=True,
            rth=False,
        )
    except NotImplementedError:
        return

    validate_data_range(data=data, start_date=start_date, end_date=end_date)
    assert data.iloc[-1].name.date() == date.today()


@pytest.mark.parametrize("provider", [provider for provider in HIST_PROVIDERS])
def test_retrieving_intermittently_cached_daily(tmpdir, provider):
    retriever = HistoricalRetriever(provider=provider, hist_data_dir=tmpdir)

    start_date = date(2020, 3, 3)
    end_date = date(2020, 3, 3)

    contract = StockContract(symbol="SPY")

    try:
        retriever.retrieve_bar_data(
            contract=contract,
            start_date=start_date,
            end_date=end_date,
            bar_size=timedelta(days=1),
        )
    except NotImplementedError:  # todo: fix
        return

    start_date = date(2020, 3, 5)
    end_date = date(2020, 3, 5)

    retriever.retrieve_bar_data(
        contract=contract,
        start_date=start_date,
        end_date=end_date,
        bar_size=timedelta(days=1),
    )

    start_date = date(2020, 3, 2)
    end_date = date(2020, 3, 6)

    data = retriever.retrieve_bar_data(
        contract=contract,
        start_date=start_date,
        end_date=end_date,
        bar_size=timedelta(days=1),
    )

    validate_data_range(data=data, start_date=start_date, end_date=end_date)


@pytest.mark.parametrize("provider", [provider for provider in HIST_PROVIDERS])
def test_retrieving_intermittently_cached_intraday(tmpdir, provider):
    retriever = HistoricalRetriever(provider=provider, hist_data_dir=tmpdir,)

    data = pd.DataFrame()
    dates = generate_trading_days(
        start_date=date.today() - timedelta(days=10),
        end_date=date.today() - timedelta(days=1),
    )
    date_ranges = [
        dates[1:2],
        dates[-3:-2],
        dates,
    ]
    for date_range in date_ranges:
        start_date = date_range[0]
        end_date = date_range[-1]

        contract = StockContract(symbol="SPY")

        try:
            data = retriever.retrieve_bar_data(
                contract=contract,
                start_date=start_date,
                end_date=end_date,
                bar_size=timedelta(days=1),
            )
        except NotImplementedError:  # todo: fix
            return

    validate_data_range(data=data, start_date=dates[0], end_date=dates[-1])


@pytest.mark.parametrize("provider", [provider for provider in HIST_PROVIDERS])
def test_retrieving_intermittently_cached_trades(tmpdir, provider):
    retriever = HistoricalRetriever(provider=provider, hist_data_dir=tmpdir,)

    data = pd.DataFrame()
    dates = generate_trading_days(
        start_date=date(2020, 7, 21), end_date=date(2020, 7, 23),
    )
    date_ranges = [
        dates[:1],
        dates[-1:],
        dates,
    ]
    for date_range in date_ranges:
        start_date = date_range[0]
        end_date = date_range[-1]

        contract = StockContract(symbol="SPY")

        try:
            data = retriever.retrieve_trades_data(
                contract=contract, start_date=start_date, end_date=end_date,
            )
        except NotImplementedError:
            return

    validate_data_range(data=data, start_date=dates[0], end_date=dates[-1])


def test_historical_bar_aggregator():
    start_date = date(2020, 4, 6)
    end_date = date(2020, 4, 7)

    retriever = HistoricalRetriever(hist_data_dir=TEST_DATA_DIR)
    contract = StockContract(symbol="SPY")
    base_data = retriever.retrieve_bar_data(
        contract=contract,
        start_date=start_date,
        end_date=end_date,
        bar_size=timedelta(minutes=1),
        cache_only=True,
    )

    aggregator = HistoricalAggregator(hist_data_dir=TEST_DATA_DIR)
    agg_data = aggregator.aggregate_data(
        contract=contract,
        start_date=start_date,
        end_date=end_date,
        base_bar_size=timedelta(minutes=1),
        target_bar_size=timedelta(minutes=5),
    )

    assert len(agg_data) == 156
    assert agg_data.iloc[0]["open"] == base_data.iloc[0]["open"]
    assert agg_data.iloc[0]["close"] == base_data.iloc[4]["close"]
    assert agg_data.iloc[0]["high"] == base_data.iloc[:5]["high"].max()
    assert agg_data.iloc[0]["low"] == base_data.iloc[:5]["low"].min()
    assert agg_data.iloc[0]["volume"] == base_data.iloc[:5]["volume"].sum()

    agg_data = aggregator.aggregate_data(
        contract=contract,
        start_date=start_date,
        end_date=end_date,
        base_bar_size=timedelta(minutes=1),
        target_bar_size=timedelta(minutes=10),
    )

    assert len(agg_data) == 78
