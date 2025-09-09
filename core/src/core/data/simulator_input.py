from abc import ABC
from typing import Any

from core.data import Data


class SimulatorInput(Data, ABC):

    def __init__(self):
        super().__init__()
        self._data = None

    @property
    def data(self) -> Any:
        return self._data