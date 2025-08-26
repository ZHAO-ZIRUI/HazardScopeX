import time
import carla
from abc import ABC, abstractmethod
from typing import Any
from typing_extensions import Self


class IncomingData(ABC):
    """
    来自仿真器的数据
    """

    def __init__(
            self,
            frame_id: int,
            timestamp_sim: float,
    ):
        self.frame_id : int = frame_id
        self.timestamp_sim : float = timestamp_sim
        self.timestamp_os : float = time.time()
        self._data = None

    @classmethod
    @abstractmethod
    def from_carla(cls, data: carla.SensorData) -> Self:
        """
        从 CARLA 的数据帧 ``carla.Image`` 中解析数据
        :param data: CARLA Server 返回的数据
        :return: 对象实例
        """
        raise NotImplementedError()
