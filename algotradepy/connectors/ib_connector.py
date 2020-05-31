import time
from threading import Thread
from typing import Optional

try:
    from ibapi.wrapper import EWrapper
    from ibapi.client import EClient
    from ibapi.utils import iswrapper
except ImportError as e:
    raise ImportError(
        f"Original Error: {e}"
        "\nThe IB API is not installed. Please reinstall using"
        " 'pip install algotradepy[ibapi]' or manually"
        " from https://www.interactivebrokers.com/en/index.php?f=5041."
    )

from algotradepy.connectors.utils import Subscribable

MASTER_CLIENT_ID = 0
_NEXT_VALID_CLIENT_ID = -1


def _get_client_id() -> int:
    global _NEXT_VALID_CLIENT_ID
    _NEXT_VALID_CLIENT_ID += 1
    return _NEXT_VALID_CLIENT_ID


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
    client_id : int, optional, default None
        If not provided, IBConnector keeps track of the client IDs already in
        use starting with 0, and gets the next available.

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
        client_id: Optional[int] = None,
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

        if client_id is None:
            self._client_id = _get_client_id()
        else:
            self._client_id = client_id

    @property
    def client_id(self) -> int:
        return self._client_id

    def managed_connect(self):
        self.connect(
            host=self._ip_address,
            port=self._socket_port,
            clientId=self._client_id,
        )
        time.sleep(0.5)

    def managed_disconnect(self):
        self.disconnect()
        time.sleep(0.5)


def build_and_start_connector(
    receiver: str = "workstation",
    trading_mode: str = "paper",
    socket_port: Optional[int] = None,
    client_id: Optional[int] = None,
) -> IBConnector:
    """Builds and prepares a connector for use.

    The function takes care of thread instantiation and ensure that the
    communication with the server is responsive before returning the
    instantiated connector object.

    Parameters
    ----------
    receiver : str, default "workstation"
        See IBConnector documentation for details.
    trading_mode : str, default "paper"
        See IBConnector documentation for details.
    socket_port : int, optional, default None
        See IBConnector documentation for details.
    client_id : int, optional, default None
        See IBConnector documentation for details.

    Returns
    -------
    connector : IBConnector
        The instantiated connector, ready for use.

    """

    req_id = None
    connector = None

    def update_req_id(reqId):
        nonlocal req_id
        req_id = reqId

    while req_id is None:
        connector = IBConnector(
            receiver=receiver,
            trading_mode=trading_mode,
            socket_port=socket_port,
            client_id=client_id,
        )
        connector.subscribe(
            target_fn=connector.nextValidId,
            callback=update_req_id,
            include_target_args=True,
        )
        connector.managed_connect()
        connector_thread = Thread(target=connector.run)
        connector_thread.start()
        connector.reqIds(numIds=1)

        if req_id is None:
            time.sleep(1)
            if req_id is None:
                connector.managed_disconnect()
                req_id = None  # for synchronization
            else:
                break
        else:
            break

    return connector
