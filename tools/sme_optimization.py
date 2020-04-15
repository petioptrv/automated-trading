from datetime import date, timedelta
import os

import pandas as pd

from algotradepy.algos.sme import SMETrader
from algotradepy.brokers import SimulationBroker
from algotradepy.path_utils import PROJECT_DIR

if __name__ == "__main__":
    logs_dir = PROJECT_DIR / "tools" / "optimization_logs"

    if not os.path.exists(logs_dir):
        os.makedirs(path=logs_dir)

    results = pd.DataFrame(columns=["window", "sme_offset", "final_pos", "res"])

    i = 1
    for window in range(2, 15):
        offset = 0.001
        for _ in range(9):
            broker = SimulationBroker(
                starting_funds=10000,
                transaction_cost=1,
                start_date=date(2010, 1, 1),
                end_date=date(2017, 12, 31),
                simulation_time_step=timedelta(days=1),
            )
            sme = SMETrader(
                broker=broker,
                symbol="SPY",
                bar_size=timedelta(days=1),
                window=window,
                sme_offset=offset,
                entry_n_shares=1,
                log=True,
            )
            sme.start()
            broker.run_sim(cache_only=True)

            sme.trades_log.to_csv(
                logs_dir / "{window}__{str(offset).replace('.', '_')}.csv"
            )

            results.loc[len(results)] = [
                window,
                offset,
                broker.get_position("SPY"),
                broker.acc_cash,
            ]

            progress = int(i / (9 * 13) * 100)
            print(f"#{'-' * progress}{' ' * (100 - progress)}# {progress}%")
            offset *= 2
            i += 1

    results.to_csv(logs_dir / "daily_sme.csv")
