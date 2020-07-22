import time as real_time
from datetime import date, timedelta, time, datetime

import numpy as np
import pytest

from algotradepy.sim_utils import (
    SimulationEndException,
    SimulationClock,
    ASimulationPiece,
    SimulationRunner,
)


def test_simulation_clock_single_day_1min_res():
    clock = SimulationClock(
        start_date=date(2020, 1, 2),
        end_date=date(2020, 1, 2),
        simulation_time_step=timedelta(minutes=1),
    )

    assert clock.date == date(2020, 1, 2)
    assert clock.time == time(9, 30)

    [clock.tick() for _ in range(390)]

    assert clock.time == time(16)
    with pytest.raises(SimulationEndException):
        clock.tick()


def test_simulation_clock_single_day_10min_res():
    clock = SimulationClock(
        start_date=date(2020, 1, 2),
        end_date=date(2020, 1, 2),
        simulation_time_step=timedelta(minutes=10),
    )

    [clock.tick() for _ in range(39)]

    assert clock.time == time(16)
    with pytest.raises(SimulationEndException):
        clock.tick()


def test_simulation_clock_real_time():
    clock = SimulationClock(
        start_date=date(2020, 1, 2),
        end_date=date(2020, 1, 2),
        simulation_time_step=timedelta(minutes=30),
        real_time_per_tick=1,
    )

    t1 = real_time.time()

    [clock.tick() for _ in range(2)]

    t2 = real_time.time()

    assert np.isclose(t2 - t1, 2, atol=0.1)


def test_simulation_clock_multi_day():
    clock = SimulationClock(
        start_date=date(2020, 1, 2),
        end_date=date(2020, 1, 3),
        simulation_time_step=timedelta(minutes=30),
    )

    [clock.tick() for _ in range(26)]

    assert clock.time == time(16)
    assert clock.date == date(2020, 1, 3)
    with pytest.raises(SimulationEndException):
        clock.tick()


def test_simulation_clock_multi_day_weekend():
    clock = SimulationClock(
        start_date=date(2020, 1, 3),
        end_date=date(2020, 1, 6),
        simulation_time_step=timedelta(minutes=30),
    )

    [clock.tick() for _ in range(26)]

    assert clock.time == time(16)
    assert clock.date == date(2020, 1, 6)
    with pytest.raises(SimulationEndException):
        clock.tick()


def test_simulation_clock_daily():
    clock = SimulationClock(
        start_date=date(2020, 1, 6),
        end_date=date(2020, 1, 8),
        simulation_time_step=timedelta(days=1),
    )

    [clock.tick() for _ in range(3)]

    assert clock.time == time(16)
    assert clock.date == date(2020, 1, 8)
    with pytest.raises(SimulationEndException):
        clock.tick()


@pytest.fixture
def sim_clock():
    c = SimulationClock(
        start_date=date(2020, 1, 6),
        end_date=date(2020, 1, 8),
        simulation_time_step=timedelta(minutes=1),
    )
    return c


def test_simulation_clock_advance_time(sim_clock):
    sim_clock.set_datetime(datetime(2020, 1, 6, 10))

    assert sim_clock.date == date(2020, 1, 6)
    assert sim_clock.time == time(10)


def test_simulation_clock_reverse_time(sim_clock):
    sim_clock.set_datetime(datetime(2020, 1, 6, 10))
    sim_clock.set_datetime(datetime(2020, 1, 6, 9, 30))

    assert sim_clock.time == time(9, 30)


def test_simulation_clock_advance_date(sim_clock):
    sim_clock.set_datetime(datetime(2020, 1, 7, 11))

    assert sim_clock.date == date(2020, 1, 7)
    assert sim_clock.time == time(11)


def test_simulation_clock_reverse_date(sim_clock):
    sim_clock.set_datetime(datetime(2020, 1, 7, 9, 30))
    sim_clock.set_datetime(datetime(2020, 1, 6, 9, 30))

    assert sim_clock.date == date(2020, 1, 6)

    with pytest.raises(ValueError):
        sim_clock.set_datetime(datetime(2019, 1, 8))

    with pytest.raises(ValueError):
        sim_clock.set_datetime(datetime(2020, 1, 8, 10, 0, 30))

    with pytest.raises(ValueError):
        sim_clock.set_datetime(datetime(2020, 1, 8, 8))


def test_simulation_runner(sim_clock):
    class DummyPiece(ASimulationPiece):
        def __init__(self):
            super().__init__()
            self.steps = 0

        def step(self, cache_only: bool = True):
            self.steps += 1

    first_piece = DummyPiece()
    second_piece = DummyPiece()
    runner = SimulationRunner(
        sim_clock=sim_clock, data_providers=[first_piece], data_consumers=[],
    )

    sim_clock.set_datetime(datetime(2020, 1, 7, 9, 30))
    runner.run_sim(step_count=1)

    assert first_piece.steps == 1
    assert second_piece.steps == 0

    runner.add_provider(sim_piece=second_piece)
    runner.run_sim(step_count=1)

    assert first_piece.steps == 2
    assert second_piece.steps == 1
    assert first_piece.sim_clock.datetime == datetime(2020, 1, 7, 9, 32)
    assert second_piece.sim_clock.datetime == datetime(2020, 1, 7, 9, 32)
