from typing import Optional

try:
    from ib_insync import IB
except ImportError as e:
    raise ImportError(
        f"Original Error: {e}"
        "\nThe IB API is not installed. Please reinstall using"
        " 'pip install algotradepy[ibapi]' or manually"
        " from https://www.interactivebrokers.com/en/index.php?f=5041."
    )

from algotradepy.subscribable import Subscribable

MASTER_CLIENT_ID = 0
_NEXT_VALID_CLIENT_ID = -1
SERVER_BUFFER_TIME = 0.1


def _get_client_id() -> int:
    global _NEXT_VALID_CLIENT_ID
    _NEXT_VALID_CLIENT_ID += 1
    return _NEXT_VALID_CLIENT_ID


class IBConnector(IB):
    """A wrapper around `ib_insync.IB`."""

    def __init__(self):
        Subscribable.__init__(self)
        IB.__init__(self)
        self._client_id = None

    @property
    def client_id(self) -> Optional[int]:
        return self._client_id

    def connect(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
        timeout: float = 4,
        readonly: bool = False,
        account: str = "",
    ):
        IB.connect(
            self=self,
            host=host,
            port=port,
            clientId=client_id,
            timeout=timeout,
            readonly=readonly,
            account=account,
        )
        self._client_id = client_id


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

    Notes
    -----
    Socket Port Mapping:
    +---------------+----------------+-------------+
    | `receiver`    | `trading_mode` | Socket Port |
    +---------------+----------------+-------------+
    | "workstation" | "live"         | 7496        |
    +---------------+----------------+-------------+
    | "workstation" | "paper"        | 7497        |
    +---------------+----------------+-------------+
    | "gateway"     | "live"         | 4001        |
    +---------------+----------------+-------------+
    | "gateway"     | "paper"        | 4002        |
    +---------------+----------------+-------------+

    """

    ip_address = "127.0.0.1"

    if socket_port is not None:
        socket_port = socket_port
    elif receiver == "workstation" and trading_mode == "live":
        socket_port = 7496
    elif receiver == "workstation" and trading_mode == "paper":
        socket_port = 7497
    elif receiver == "gateway" and trading_mode == "live":
        socket_port = 4001
    elif receiver == "gateway" and trading_mode == "paper":
        socket_port = 4002
    else:
        raise ValueError(
            f"Unrecognized socket port configuration receiver={receiver}"
            f" trading_mode={trading_mode}. Please consult the"
            f" documentation for valid values."
        )

    if client_id is None:
        client_id = _get_client_id()

    connector = IBConnector()
    connector.connect(host=ip_address, port=socket_port, client_id=client_id)

    return connector
