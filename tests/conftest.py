import os
from datetime import date, timedelta
from pathlib import Path

import pytest

from algotradepy.brokers import SimulationBroker
from algotradepy.contracts import Currency
from algotradepy.historical.loaders import HistoricalRetriever
from algotradepy.sim_utils import SimulationClock, SimulationRunner
from algotradepy.streamers.sim_streamer import SimulationDataStreamer

CURRENT_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
PROJECT_DIR = CURRENT_DIR.parent
TEST_DATA_DIR = CURRENT_DIR / "test_hist_data"


@pytest.fixture
def sim_broker_runner_and_streamer_15m():
    sim_clock = SimulationClock(
        start_date=date(2020, 4, 6),
        end_date=date(2020, 4, 7),
        simulation_time_step=timedelta(minutes=15),
    )
    streamer = SimulationDataStreamer(
        historical_retriever=HistoricalRetriever(hist_data_dir=TEST_DATA_DIR),
    )
    broker = SimulationBroker(
        sim_streamer=streamer,
        starting_funds={Currency.USD: 1_000},
        transaction_cost=1,
    )
    sim_runner = SimulationRunner(
        sim_clock=sim_clock,
        data_providers=[streamer],
        data_consumers=[broker],
    )
    return broker, sim_runner, streamer
