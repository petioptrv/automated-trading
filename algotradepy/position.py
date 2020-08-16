from algotradepy.contracts import AContract

from algotradepy.utils import ReprAble


class Position(ReprAble):
    def __init__(
        self, contract: AContract, position: float, ave_fill_price: float,
    ):
        ReprAble.__init__(self)
        self._contract = contract
        self._position = position
        self._ave_fill_price = ave_fill_price

    @property
    def contract(self) -> AContract:
        return self._contract

    @property
    def position(self) -> float:
        return self._position

    @property
    def ave_fill_price(self) -> float:
        return self._ave_fill_price
