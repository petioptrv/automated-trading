from datetime import timedelta, date

from algotradepy.historical.loaders import HistoricalRetriever
from algotradepy.historical.historical_providers import YahooHistoricalProvider

if __name__ == "__main__":
    provider = YahooHistoricalProvider()
    hr = HistoricalRetriever(provider=provider)
    end_date = date.today()
    hr.retrieve_bar_data(
        symbol="SPY",
        bar_size=timedelta(days=1),
        start_date=date(2000, 1, 1),
        end_date=end_date,
    )
