from datetime import date, timedelta

from algotradepy.contracts import StockContract
from algotradepy.historical.transformers import HistoricalAggregator

if __name__ == "__main__":
    aggregator = HistoricalAggregator()
    aggregator.aggregate_data(
        contract=StockContract(symbol="SPY"),
        start_date=date(2020, 4, 8),
        end_date=date(2020, 4, 8),
        base_bar_size=timedelta(minutes=1),
        target_bar_size=timedelta(minutes=60),
    )
