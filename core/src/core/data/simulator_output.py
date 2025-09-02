import time
from typing import Any

import carla
from abc import ABC, abstractmethod
from typing_extensions import Self

from core.data import Data


class SimulatorOutput(Data, ABC):
    """
    来自仿真器的数据
    """

    def __init__(
            self,
            frame_id: int,
            timestamp_sim: float,
    ):
        super().__init__()
        self.frame_id : int = frame_id
        self.timestamp_sim : float = timestamp_sim
        self.timestamp_os : float = time.time()
        self._data = None

    @property
    def data(self) -> Any:
        return self._data

    @classmethod
    @abstractmethod
    def from_carla(cls, data: carla.SensorData) -> Self:
        """
        从 CARLA 的数据帧 ``carla.SensorData`` 中解析数据
        :param data: CARLA Server 返回的数据
        :return: 对象实例
        """
        raise NotImplementedError()

