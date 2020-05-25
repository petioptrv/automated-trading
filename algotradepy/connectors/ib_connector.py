from typing import Optional

try:
    from ibapi.wrapper import EWrapper
    from ibapi.client import EClient
    from ibapi.utils import (
        iswrapper,
    )
except ImportError as e:
    raise ImportError(
        f"Original Error: {e}"
        "\nThe IB API is not installed. Please reinstall using"
        " 'pip install algotradepy[ibapi]' or manually"
        " from https://www.interactivebrokers.com/en/index.php?f=5041."
    )

from algotradepy.connectors.utils import Subscribable

NEXT_VALID_CLIENT_ID = -1


def _get_client_id() -> int:
    global NEXT_VALID_CLIENT_ID
    NEXT_VALID_CLIENT_ID += 1
    return NEXT_VALID_CLIENT_ID


class IBConnector(EWrapper, EClient, Subscribable):
    """The IB API Connector.

    This class establishes a connection to TWS. Its use consists in masking the
    threaded nature of the communication and expose a synchronous API.

    Parameters
    ----------
    receiver : str, default "workstation"
        The application that will be on the other end of the connection.
        Accepted values are "workstation" and "gateway". Used together with
        trading_mode parameter to determine the socket port (see Notes for
        socket port mapping).
    trading_mode : str, default "paper"
        Determine the trading mode. Valid values are "paper" and "live".
        Used together with receiver parameter to determine the socket port
        (see Notes for socket port mapping).
    socket_port : int, optional, default None
        Specifies the socket port to use for the connection. If provided,
        receiver and trading_mode parameters are ignored.

    Notes
    -----
    Socket Port Mapping:
    +---------------+----------------+-------------+
    | `receiver`    | `trading_mode` | Socket Port |
    +---------------+----------------+-------------+
    | "workstation" | "paper"        | 7497        |
    +---------------+----------------+-------------+
    | "workstation" | "live"         | todo: get   |
    +---------------+----------------+-------------+
    | "gateway"     | "paper"        | todo: get   |
    +---------------+----------------+-------------+
    | "gateway"     | "live"         | todo: get   |
    +---------------+----------------+-------------+
    """

    def __init__(
            self,
            receiver: str = "workstation",
            trading_mode: str = "paper",
            socket_port: Optional[int] = None,
    ):
        Subscribable.__init__(self)
        EWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)

        self._ip_address = "127.0.0.1"
        if socket_port is not None:
            self._socket_port = socket_port
        elif receiver == "workstation" and trading_mode == "paper":
            self._socket_port = 7497
        elif receiver == "workstation" and trading_mode == "live":
            raise ValueError("Socket port not yet set.")
        elif receiver == "gateway" and trading_mode == "paper":
            raise ValueError("Socket port not yet set.")
        elif receiver == "gateway" and trading_mode == "live":
            raise ValueError("Socket port not yet set.")
        else:
            raise ValueError(
                f"Unrecognized socket port configuration receiver={receiver}"
                f" trading_mode={trading_mode}. Please consult the"
                f" documentation for valid values."
            )
        self._client_id = _get_client_id()

        self.connect(
            host=self._ip_address,
            port=self._socket_port,
            clientId=self._client_id,
        )

    def stop(self):
        self.disconnect()
