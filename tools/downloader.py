from datetime import timedelta, date

from algotradepy.historical.loaders import HistoricalRetriever
from algotradepy.historical.providers import YahooProvider

if __name__ == "__main__":
    provider = YahooProvider()
    hr = HistoricalRetriever(provider=provider)
    end_date = date(2020, 3, 11) - timedelta(days=0)
    hr.retrieve_bar_data(
        symbol="SPY",
        bar_size=timedelta(minutes=1),
        start_date=end_date-timedelta(days=6),
        end_date=end_date,
    )
