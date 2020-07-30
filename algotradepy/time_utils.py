from datetime import date, time, timedelta, datetime
from typing import List

import pandas_market_calendars as pmc
import pandas as pd


def generate_trading_days(start_date: date, end_date: date) -> List[date]:
    nyse = pmc.get_calendar("NYSE")
    schedule = nyse.schedule(start_date=start_date, end_date=end_date)
    dates = schedule.index.date.tolist()
    return dates


def generate_trading_schedule(
    start_date: date, end_date: date,
) -> pd.DataFrame:
    nyse = pmc.get_calendar("NYSE")
    schedule = nyse.schedule(start_date=start_date, end_date=end_date)
    schedule.loc[:, "market_open"] = schedule["market_open"].apply(
        lambda x: x.tz_convert("America/New_York").time()
    )
    schedule.loc[:, "market_close"] = schedule["market_close"].apply(
        lambda x: x.tz_convert("America/New_York").time()
    )
    schedule.index = schedule.index.date
    return schedule


def get_next_trading_date(base_date: date) -> date:
    end_date = base_date + timedelta(days=5)
    schedule = generate_trading_schedule(
        start_date=base_date, end_date=end_date,
    )
    target_date = schedule.iloc[1].name
    return target_date


def time_arithmetic(start_time: time, delta: timedelta,) -> time:
    dt = datetime.combine(date.today(), start_time)
    res_dt = dt + delta

    if dt.date() != res_dt.date():
        raise ValueError(
            f"Undefined behaviour when adding {delta} to {start_time}."
        )

    end_time = res_dt.time()
    return end_time


def is_time_aware(dt) -> bool:
    is_aware = dt.tzinfo is not None or dt.tzinfo.utcoffset(dt) is not None
    return is_aware


def milli_to_seconds(milli: int) -> float:
    s = milli / 1e3
    return s


def nano_to_seconds(nano: int) -> float:
    s = nano / 1e9
    return s


def seconds_to_nano(s: float) -> int:
    nano = int(s * 1e9)
    return nano
