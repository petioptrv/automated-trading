import os
from datetime import datetime, date, timedelta
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

from algotradepy.algos.sme import SMETrader
from algotradepy.brokers import SimulationBroker, SimulationClock
from algotradepy.historical.loaders import HistoricalRetriever


def prepare_dataset(data_dir: Path, case: int):
    f_dir = data_dir / "TEST" / "5 m"
    os.makedirs(str(f_dir))
    f_path = f_dir / "2020-04-06.csv"

    index = pd.date_range(
        start=datetime(2020, 4, 6, 9, 30),
        end=datetime(2020, 4, 6, 15, 55),
        freq="15min",
    )
    data = pd.DataFrame(
        data={
            "open": np.full(len(index), 100),
            "high": np.full(len(index), 100),
            "low": np.full(len(index), 100),
            "close": np.full(len(index), 100),
            "volume": np.full(len(index), 1000),
        },
        index=index
    )

    # ================= LONGS ====================

    # sme -> above upper -> below sme
    if case == 0:
        data.iloc[10].loc[["high", "close"]] = [111, 111]
        data.iloc[11].loc[["open", "high", "low", "close"]] = [
            111, 111, 95, 95
        ]
        data.iloc[12].loc[["open", "low"]] = [95, 95]  # for completeness

    # sme -> above upper -> below upper -> below sme
    elif case == 1:
        pass

    # sme -> above upper -> below upper -> above upper -> below sme

    # ================= SHORTS ====================

    # sme -> below lower -> above sme

    # sme -> below lower -> above lower -> above sme

    # sme -> below lower -> above lower -> below lower -> above sme

    # ================== OTHER ======================

    # sme -> below upper -> above lower

    # long, go below lower, go above sme

    # ================== FAILURES ===================

    # sme -> 10 x above upper -> below new lower

    data.to_csv(f_path)


def get_sme_sim_broker(data_dir):
    clock = SimulationClock(
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 6),
        simulation_time_step=timedelta(minutes=5),
    )
    retriever = HistoricalRetriever(hist_data_dir=data_dir)
    broker = SimulationBroker(
        starting_funds=10_000,
        transaction_cost=1,
        sim_clock=clock,
        hist_retriever=retriever,
    )
    trader = SMETrader(
        broker=broker,
        symbol="TEST",
        bar_size=timedelta(minutes=5),
        window=10,
        sme_offset=.1,
        entry_n_shares=1,
    )
    trader.start()
    return broker


@pytest.mark.parametrize(
    "case,expected_acc_cash,expected_pos",
    [
        (0, 10_016, 0),
    ]
)
def test_cases(tmpdir, case, expected_acc_cash, expected_pos):
    data_dir = Path(tmpdir)
    prepare_dataset(data_dir=data_dir, case=case)
    broker = get_sme_sim_broker(data_dir=data_dir)

    broker.run_sim(cache_only=True)

    assert broker.acc_cash == expected_acc_cash
    assert broker.get_position("TEST") == expected_pos
