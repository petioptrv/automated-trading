from datetime import timedelta, date
from typing import Optional

from algotradepy.path_utils import PROJECT_DIR
from algotradepy.time_utils import generate_trading_days

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"


def is_daily(bar_size: timedelta):
    daily = bar_size == timedelta(days=1)
    return daily


def bar_size_to_str(bar_size: Optional[timedelta]):
    if bar_size == timedelta(0):
        bar_size_str = "tick"
    elif bar_size == timedelta(seconds=1):
        bar_size_str = "1 sec"
    elif bar_size < timedelta(minutes=1):
        bar_size_str = f"{bar_size.seconds} secs"
    elif bar_size == timedelta(minutes=1):
        bar_size_str = "1 min"
    elif bar_size < timedelta(hours=1):
        bar_size_str = f"{int(bar_size.seconds / 60)} mins"
    elif bar_size == timedelta(hours=1):
        bar_size_str = "1 hour"
    elif bar_size < timedelta(days=1):
        bar_size_str = f"{int(bar_size.seconds / 60 / 60)} hours"
    else:
        bar_size_str = "."

    return bar_size_str


def hist_file_names(
    start_date: date, end_date: date, bar_size: timedelta,
):
    if is_daily(bar_size=bar_size):
        f_names = ["daily.csv"]
    else:
        dates = generate_trading_days(start_date=start_date, end_date=end_date)
        f_names = [f"{date_.strftime(DATE_FORMAT)}.csv" for date_ in dates]

    return f_names


HIST_DATA_DIR = PROJECT_DIR / "histData"
