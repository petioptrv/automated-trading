from algotradepy.historical.providers.yahoo_provider import (
    YahooHistoricalProvider,
)
from algotradepy.historical.providers.iex_provider import IEXHistoricalProvider
from algotradepy.historical.loaders import HistoricalRetriever
from algotradepy.historical.transformers import HistoricalAggregator

__all__ = [
    "YahooHistoricalProvider",
    "IEXHistoricalProvider",
    "HistoricalRetriever",
    "HistoricalAggregator",
]

try:
    from algotradepy.historical.providers.polygon_provider import (
        PolygonHistoricalProvider,
    )

    __all__.append("PolygonHistoricalProvider")
except ImportError:
    pass
