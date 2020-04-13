from datetime import date, timedelta

from algotradepy.historical import HistoricalAggregator

if __name__ == "__main__":
    aggregator = HistoricalAggregator()
    aggregator.aggregate_data(
        symbol="SPY",
        start_date=date(2020, 3, 11),
        end_date=date(2020, 4, 7),
        base_bar_size=timedelta(minutes=1),
        target_bar_size=timedelta(minutes=60),
    )
