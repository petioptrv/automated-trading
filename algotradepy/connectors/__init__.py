from algotradepy.connectors.iex_connector import IEXConnector

__all__ = ["IEXConnector"]

try:
    from algotradepy.connectors.polygon_connector import (
        PolygonWebSocketConnector,
        PolygonWSClusters,
        PolygonRESTConnector,
    )

    __all__.extend(
        [
            "PolygonWebSocketConnector",
            "PolygonWSClusters",
            "PolygonRESTConnector",
        ],
    )
except ImportError:
    pass

try:
    from algotradepy.connectors.ib_connector import IBConnector

    __all__.append("IBConnector")
except ImportError:
    pass
