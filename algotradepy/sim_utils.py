import time as real_time
from abc import ABC, abstractmethod
from datetime import date, timedelta, datetime, time
from typing import Optional, List

from algotradepy.historical.hist_utils import is_daily
from algotradepy.time_utils import generate_trading_schedule


class SimulationEndException(Exception):
    pass


class SimulationClock:
    def __init__(
        self,
        start_date: date,
        end_date: date,
        simulation_time_step: timedelta = timedelta(minutes=1),
        real_time_per_tick: int = 0,
    ):
        self._start_date = start_date
        self._end_date = end_date
        self._time_step = simulation_time_step
        self._time_per_tick = real_time_per_tick
        self._schedule = generate_trading_schedule(
            start_date=start_date, end_date=end_date,
        )
        self._curr_schedule_index = 0
        self._clock_dt = datetime.combine(
            self._schedule.index[0], self._schedule.iloc[0]["market_open"],
        )

    @property
    def start_date(self) -> date:
        return self._start_date

    @property
    def end_date(self) -> date:
        return self._end_date

    @property
    def time_step(self) -> timedelta:
        return self._time_step

    @property
    def date(self) -> date:
        curr_date = self._clock_dt.date()
        return curr_date

    @property
    def time(self) -> time:
        curr_time = self._clock_dt.time()
        return curr_time

    @property
    def datetime(self) -> datetime:
        return self._clock_dt

    @property
    def start_of_day(self) -> bool:
        idx = self._curr_schedule_index
        open_time = self._schedule.iloc[idx]["market_open"]
        sod = self._clock_dt.time() == open_time
        return sod

    @property
    def end_of_day(self) -> bool:
        idx = self._curr_schedule_index
        close_time = self._schedule.iloc[idx]["market_close"]
        eod = self._clock_dt.time() == close_time
        return eod

    def tick(self):
        real_time.sleep(self._time_per_tick)

        if is_daily(bar_size=self._time_step):
            self._tick_daily()
        else:
            self._tick_intraday()

    def set_datetime(self, dt: datetime):
        if not self._start_date <= dt.date() <= self._end_date:
            raise ValueError(
                f"Date must be between {self._start_date} and"
                f" {self._end_date}. Got {dt.date()}."
            )

        day = self._schedule.loc[dt.date()]

        if not day["market_open"] <= dt.time() < day["market_close"]:
            raise ValueError(
                f"Time must be between {day['market_open']} and"
                f" {day['market_close']}. Got {dt.time()}."
            )

        time_ = dt.time()
        td = timedelta(
            hours=time_.hour, minutes=time_.minute, seconds=time_.second,
        )
        if not td % self._time_step == timedelta():
            raise ValueError(
                f"Cannot set time {time_} for time-step {self._time_step}."
            )

        dates_list = self._schedule.index.to_list()
        idx = dates_list.index(dt.date())

        self._curr_schedule_index = idx
        self._clock_dt = datetime.combine(dt.date(), dt.time())

    def _tick_daily(self):
        idx = self._curr_schedule_index

        if idx == len(self._schedule):
            raise SimulationEndException

        self._clock_dt = datetime.combine(
            self._schedule.index[idx],
            self._schedule.iloc[idx]["market_close"],
        )
        self._curr_schedule_index += 1

    def _tick_intraday(self):
        self._clock_dt += self._time_step

        idx = self._curr_schedule_index
        close_time = self._schedule.iloc[idx]["market_close"]

        if self._clock_dt.time() > close_time:
            day_switch = True
        else:
            day_switch = False

        if day_switch:
            self._curr_schedule_index += 1

            if self._curr_schedule_index == len(self._schedule):
                raise SimulationEndException

            idx = self._curr_schedule_index
            self._clock_dt = datetime.combine(
                self._schedule.index[idx],
                self._schedule.iloc[idx]["market_open"],
            )
            self._clock_dt += self._time_step


class ASimulationPiece(ABC):
    def __init__(self, *args, **kwargs):
        self._sim_clock = None

    @property
    def sim_clock(self) -> SimulationClock:
        return self._sim_clock

    @sim_clock.setter
    def sim_clock(self, sim_clock: SimulationClock):
        self._sim_clock = sim_clock

    @abstractmethod
    def step(self, cache_only: bool = True):
        raise NotImplementedError


class SimulationRunner:
    def __init__(
        self,
        sim_clock: SimulationClock,
        data_providers: List[ASimulationPiece],
        data_consumers: List[ASimulationPiece],
    ):
        self._sim_clock = sim_clock
        self._data_providers = data_providers
        self._data_consumers = data_consumers

        for piece in self._data_providers:
            piece.sim_clock = sim_clock
        for piece in self._data_consumers:
            piece.sim_clock = sim_clock

    def add_provider(self, sim_piece: ASimulationPiece):
        sim_piece.sim_clock = self._sim_clock
        self._data_providers.append(sim_piece)

    def remove_provider(self, sim_piece: ASimulationPiece):
        self._data_providers.remove(sim_piece)

    def add_consumer(self, sim_piece: ASimulationPiece):
        sim_piece.sim_clock = self._sim_clock
        self._data_consumers.append(sim_piece)

    def remove_consumer(self, sim_piece: ASimulationPiece):
        self._data_consumers.remove(sim_piece)

    def run_sim(
        self, step_count: Optional[int] = None, cache_only: bool = True,
    ):
        assert step_count is None or step_count >= 0

        while step_count != 0:
            try:
                self._sim_clock.tick()
                for piece in self._data_providers:
                    piece.step(cache_only=cache_only)
                for piece in self._data_consumers:
                    piece.step(cache_only=cache_only)
            except SimulationEndException:
                break

            if step_count is not None:
                step_count -= 1
