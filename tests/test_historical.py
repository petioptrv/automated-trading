from datetime import date, timedelta
from typing import Optional

import pandas as pd
import numpy as np
import pytest

from algotradepy.historical.loaders import HistoricalRetriever
from algotradepy.historical.providers import YahooProvider, IEXProvider
from algotradepy.historical.transformers import HistoricalAggregator
from algotradepy.time_utils import generate_trading_days
from tests.conftest import TEST_DATA_DIR


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


def test_retriever_cached_daily():
    start_date = date(2020, 4, 1)
    end_date = date(2020, 4, 2)

    retriever = HistoricalRetriever(hist_data_dir=TEST_DATA_DIR)
    data = retriever.retrieve_bar_data(
        symbol="SPY",
        start_date=start_date,
        end_date=end_date,
        bar_size=timedelta(days=1),
        cache_only=True,
    )

    assert len(data) != 0

    validate_data_range(data=data, start_date=start_date, end_date=end_date)


HIST_PROVIDERS = [
    YahooProvider(),
    IEXProvider(
        api_token="Tpk_98c62e8146894c4985dfb98034d7ac87"
    ),  # todo: remove simulation token
]


@pytest.mark.parametrize("provider", [provider for provider in HIST_PROVIDERS])
def test_retrieve_non_cached_daily(tmpdir, provider):
    start_date = date(2020, 4, 1)
    end_date = date(2020, 4, 2)

    retriever = HistoricalRetriever(provider=provider, hist_data_dir=tmpdir,)
    data = retriever.retrieve_bar_data(
        symbol="SPY",
        start_date=start_date,
        end_date=end_date,
        bar_size=timedelta(days=1),
    )

    validate_data_range(data=data, start_date=start_date, end_date=end_date)


@pytest.mark.parametrize("provider", [provider for provider in HIST_PROVIDERS])
def test_retrieve_non_cached_intraday(tmpdir, provider):
    start_date = date.today() - timedelta(days=7)
    end_date = date.today() - timedelta(days=1)

    retriever = HistoricalRetriever(provider=provider, hist_data_dir=tmpdir,)
    data = retriever.retrieve_bar_data(
        symbol="SPY",
        start_date=start_date,
        end_date=end_date,
        bar_size=timedelta(minutes=1),
    )

    validate_data_range(data=data, start_date=start_date, end_date=end_date)
    assert np.isclose(len(data), 5 * 6.5 * 60, atol=7 * 60)


@pytest.mark.parametrize("provider", [provider for provider in HIST_PROVIDERS])
def test_retrieving_intermittently_cached_daily(tmpdir, provider):
    retriever = HistoricalRetriever(provider=provider, hist_data_dir=tmpdir,)

    start_date = date(2020, 3, 3)
    end_date = date(2020, 3, 3)

    retriever.retrieve_bar_data(
        symbol="SPY",
        start_date=start_date,
        end_date=end_date,
        bar_size=timedelta(days=1),
    )

    start_date = date(2020, 3, 5)
    end_date = date(2020, 3, 5)

    retriever.retrieve_bar_data(
        symbol="SPY",
        start_date=start_date,
        end_date=end_date,
        bar_size=timedelta(days=1),
    )

    start_date = date(2020, 3, 2)
    end_date = date(2020, 3, 6)

    data = retriever.retrieve_bar_data(
        symbol="SPY",
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

        data = retriever.retrieve_bar_data(
            symbol="SPY",
            start_date=start_date,
            end_date=end_date,
            bar_size=timedelta(days=1),
        )

    validate_data_range(data=data, start_date=dates[0], end_date=dates[-1])


def test_historical_bar_aggregator():
    start_date = date(2020, 4, 6)
    end_date = date(2020, 4, 7)

    retriever = HistoricalRetriever(hist_data_dir=TEST_DATA_DIR)
    base_data = retriever.retrieve_bar_data(
        symbol="SPY",
        start_date=start_date,
        end_date=end_date,
        bar_size=timedelta(minutes=1),
        cache_only=True,
    )

    aggregator = HistoricalAggregator(hist_data_dir=TEST_DATA_DIR)
    agg_data = aggregator.aggregate_data(
        symbol="SPY",
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
        symbol="SPY",
        start_date=start_date,
        end_date=end_date,
        base_bar_size=timedelta(minutes=1),
        target_bar_size=timedelta(minutes=10),
    )

    assert len(agg_data) == 78
