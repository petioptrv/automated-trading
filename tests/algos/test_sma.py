import os
from datetime import datetime, date, timedelta, time
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

from algotradepy.algos.sma import SMATrader
from algotradepy.brokers.sim_broker import SimulationBroker
from algotradepy.historical.loaders import HistoricalRetriever
from algotradepy.time_utils import generate_trading_days


def apply_case(data: pd.DataFrame, case: int):
    # Case: Above upper to above upper
    # sme -> above upper -> above upper -> below sme
    if case == 0:
        data.iloc[11].loc[["high", "close"]] = [111, 111]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [
            111,
            111,
            113,
            113,
        ]
        data.iloc[13].loc[["open", "high", "low", "close"]] = [
            111,
            111,
            95,
            95,
        ]
        data.iloc[14].loc[["open", "low"]] = [95, 95]  # for completeness

    # Case: Above upper to above sme
    # sme -> above upper -> above sme -> below sme
    if case == 1:
        data.iloc[11].loc[["high", "close"]] = [111, 111]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [
            111,
            111,
            102,
            102,
        ]
        data.iloc[13].loc[["open", "high", "low", "close"]] = [
            102,
            102,
            95,
            95,
        ]
        data.iloc[14].loc[["open", "low"]] = [95, 95]  # for completeness

    # Case: Above upper to below sme
    # sme -> above upper -> below sme
    elif case == 2:
        data.iloc[11].loc[["high", "close"]] = [111, 111]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [
            111,
            111,
            95,
            95,
        ]
        data.iloc[13].loc[["open", "low"]] = [95, 95]  # for completeness

    # Case: Above upper to below lower
    # sme -> above upper -> below lower -> above sme
    elif case == 3:
        data.iloc[11].loc[["high", "close"]] = [111, 111]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [
            111,
            111,
            90,
            90,
        ]
        data.iloc[13].loc[["open", "high", "low", "close"]] = [
            90,
            105,
            90,
            105,
        ]
        data.iloc[14].loc[["open", "high"]] = [105, 105]  # for completeness

    # Case: Above sme to above upper
    # sme -> above sme -> above upper -> below sme
    elif case == 4:
        data.iloc[11].loc[["high", "close"]] = [101, 101]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [
            101,
            111,
            101,
            111,
        ]
        data.iloc[13].loc[["open", "high", "low", "close"]] = [
            111,
            111,
            95,
            95,
        ]
        data.iloc[14].loc[["open", "low"]] = [95, 95]  # for completeness

    # Case: Above sme to above sme
    # sme -> above sme -> above sme
    elif case == 5:
        data.iloc[11].loc[["high", "close"]] = [101, 101]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [
            101,
            102,
            101,
            102,
        ]
        data.iloc[13].loc[["open", "high"]] = [102, 102]  # for completeness

    # Case: Above sme to below sme
    # sme -> above sme -> below sme
    elif case == 6:
        data.iloc[11].loc[["high", "close"]] = [101, 101]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [
            101,
            101,
            99,
            99,
        ]
        data.iloc[13].loc[["open", "low"]] = [99, 99]  # for completeness

    # Case: Above sme to below lower
    # sme -> above sme -> below lower -> above sme
    elif case == 7:
        data.iloc[11].loc[["high", "close"]] = [101, 101]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [
            101,
            101,
            89,
            89,
        ]
        data.iloc[13].loc[["open", "high", "low", "close"]] = [
            89,
            105,
            89,
            105,
        ]
        data.iloc[14].loc[["open", "high"]] = [105, 105]  # for completeness

    # Case: Below sme to above upper
    # sme -> below sme -> above upper -> below sme
    elif case == 8:
        data.iloc[11].loc[["low", "close"]] = [99, 99]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [
            99,
            111,
            99,
            111,
        ]
        data.iloc[13].loc[["open", "high", "low", "close"]] = [
            111,
            111,
            95,
            95,
        ]
        data.iloc[14].loc[["open", "low"]] = [95, 95]  # for completeness

    # Case: Below sme to above sme
    # sme -> below sme -> above sme
    elif case == 9:
        data.iloc[11].loc[["low", "close"]] = [99, 99]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [
            99,
            101,
            99,
            101,
        ]
        data.iloc[13].loc[["open", "high"]] = [101, 101]  # for completeness

    # Case: Below sme to below sme
    # sme -> below sme -> below sme
    elif case == 10:
        data.iloc[11].loc[["low", "close"]] = [99, 99]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [99, 99, 98, 98]
        data.iloc[13].loc[["open", "low"]] = [98, 98]  # for completeness

    # Case: Below sme to below lower
    # sme -> below sme -> below lower -> above sme
    elif case == 11:
        data.iloc[11].loc[["low", "close"]] = [99, 99]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [99, 99, 88, 88]
        data.iloc[13].loc[["open", "high", "low", "close"]] = [
            88,
            105,
            88,
            105,
        ]
        data.iloc[14].loc[["open", "high"]] = [105, 105]  # for completeness

    # Case: Below lower to above upper
    # sme -> below lower -> above upper -> below sme
    elif case == 12:
        data.iloc[11].loc[["low", "close"]] = [89, 89]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [
            89,
            111,
            89,
            111,
        ]
        data.iloc[13].loc[["open", "high", "low", "close"]] = [
            111,
            111,
            95,
            95,
        ]
        data.iloc[14].loc[["open", "low"]] = [95, 95]  # for completeness

    # Case: Below lower to above sme
    # sme -> below lower -> above sme
    elif case == 13:
        data.iloc[11].loc[["low", "close"]] = [89, 89]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [
            89,
            105,
            89,
            105,
        ]
        data.iloc[13].loc[["open", "high"]] = [105, 105]  # for completeness

    # Case: Below lower to below sme
    # sme -> below lower -> below sme -> above sme
    elif case == 14:
        data.iloc[11].loc[["low", "close"]] = [89, 89]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [89, 95, 89, 95]
        data.iloc[13].loc[["open", "high", "low", "close"]] = [
            95,
            105,
            95,
            105,
        ]
        data.iloc[14].loc[["open", "high"]] = [105, 105]  # for completeness

    # Case: Below lower to below lower
    # sme -> below lower -> below lower -> above sme
    elif case == 15:
        data.iloc[11].loc[["low", "close"]] = [89, 89]
        data.iloc[12].loc[["open", "high", "low", "close"]] = [89, 89, 88, 88]
        data.iloc[13].loc[["open", "high", "low", "close"]] = [
            88,
            105,
            88,
            105,
        ]
        data.iloc[14].loc[["open", "high"]] = [105, 105]  # for completeness


def prepare_dataset_intra_single_day(data_dir: Path, case: int):
    f_dir = data_dir / "TEST" / "5 mins"
    os.makedirs(str(f_dir))
    f_path = f_dir / "2020-04-06.csv"

    index = pd.date_range(
        start=datetime(2020, 4, 6, 9, 30),
        end=datetime(2020, 4, 6, 15, 55),
        freq="5min",
        name="datetime",
    )
    data = pd.DataFrame(
        data={
            "open": np.full(len(index), 100),
            "high": np.full(len(index), 100),
            "low": np.full(len(index), 100),
            "close": np.full(len(index), 100),
            "volume": np.full(len(index), 1000),
        },
        index=index,
    )

    apply_case(data=data, case=case)

    data.to_csv(f_path)


def get_sme_sim_broker_intra_single_day(data_dir):
    retriever = HistoricalRetriever(hist_data_dir=data_dir)
    broker = SimulationBroker(
        starting_funds=10_000,
        transaction_cost=1,
        hist_retriever=retriever,
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 6),
        simulation_time_step=timedelta(minutes=5),
    )
    trader = SMATrader(
        broker=broker,
        symbol="TEST",
        bar_size=timedelta(minutes=5),
        window=10,
        sma_offset=0.1,
        entry_n_shares=1,
        exit_start=time(15, 50),
        full_exit=time(15, 55),
    )
    trader.start()
    return broker


@pytest.mark.parametrize(
    "case,expected_acc_cash,expected_pos",
    [
        (0, 10_014, 0),
        (1, 10_014, 0),
        (2, 10_014, 0),
        (3, 10_032, 0),
        (4, 10_014, 0),
        (5, 10_000, 0),
        (6, 10_000, 0),
        (7, 10_014, 0),
        (8, 10_014, 0),
        (9, 10_000, 0),
        (10, 10_000, 0),
        (11, 10_015, 0),
        (12, 10_034, 0),
        (13, 10_014, 0),
        (14, 10_014, 0),
        (15, 10_014, 0),
    ],
)
def test_cases_intra_single_day(tmpdir, case, expected_acc_cash, expected_pos):
    data_dir = Path(tmpdir)
    prepare_dataset_intra_single_day(data_dir=data_dir, case=case)
    broker = get_sme_sim_broker_intra_single_day(data_dir=data_dir)

    broker.run_sim(cache_only=True)

    assert broker.acc_cash == expected_acc_cash
    assert broker.get_position("TEST") == expected_pos


def prepare_dataset_daily(data_dir: Path, case: int):
    f_dir = data_dir / "TEST"
    os.makedirs(str(f_dir))
    f_path = f_dir / "daily.csv"

    dates = generate_trading_days(
        start_date=datetime(2020, 2, 1), end_date=datetime(2020, 3, 31),
    )
    index = pd.DatetimeIndex(dates, name="datetime")
    data = pd.DataFrame(
        data={
            "open": np.full(len(index), 100),
            "high": np.full(len(index), 100),
            "low": np.full(len(index), 100),
            "close": np.full(len(index), 100),
            "volume": np.full(len(index), 1000),
        },
        index=index,
    )

    apply_case(data=data, case=case)

    data.to_csv(f_path)


def get_sme_sim_broker_daily(data_dir):
    retriever = HistoricalRetriever(hist_data_dir=data_dir)
    broker = SimulationBroker(
        starting_funds=10_000,
        transaction_cost=1,
        hist_retriever=retriever,
        start_date=date(2020, 2, 1),
        end_date=date(2020, 3, 31),
        simulation_time_step=timedelta(days=1),
    )
    trader = SMATrader(
        broker=broker,
        symbol="TEST",
        bar_size=timedelta(days=1),
        window=10,
        sma_offset=0.1,
        entry_n_shares=1,
    )
    trader.start()
    return broker


@pytest.mark.parametrize(
    "case,expected_acc_cash,expected_pos",
    [
        (0, 10_014, 0),
        (1, 10_014, 0),
        (2, 10_014, 0),
        (3, 10_032, 0),
        (4, 10_014, 0),
        (5, 10_000, 0),
        (6, 10_000, 0),
        (7, 10_014, 0),
        (8, 10_014, 0),
        (9, 10_000, 0),
        (10, 10_000, 0),
        (11, 10_015, 0),
        (12, 10_034, 0),
        (13, 10_014, 0),
        (14, 10_014, 0),
        (15, 10_014, 0),
    ],
)
def test_cases_daily(tmpdir, case, expected_acc_cash, expected_pos):
    data_dir = Path(tmpdir)
    prepare_dataset_daily(data_dir=data_dir, case=case)
    broker = get_sme_sim_broker_daily(data_dir=data_dir)

    broker.run_sim(cache_only=True)

    assert broker.acc_cash == expected_acc_cash
    assert broker.get_position("TEST") == expected_pos


@pytest.mark.skip("Not implemented.")
def test_closing_intraday_positions_at_eod():
    raise NotImplementedError
