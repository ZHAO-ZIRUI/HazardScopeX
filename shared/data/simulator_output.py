import time
from abc import ABC, abstractmethod
from typing import Any
from typing_extensions import Self

from shared.data import BaseData


class SimulatorOutput(BaseData, ABC):
    """
    仿真器的输出数据
    """
    def __init__(
        self, 
        sim_frame: int, 
        sim_timestamp: float,
    ):
        super().__init__()
        self._sim_frame = sim_frame
        self._sim_timestamp = sim_timestamp
        self._os_timestamp = time.time()    # 对象被创建时的操作系统时间戳

    @property
    def sim_frame(self) -> int:
        """仿真帧数"""
        return self._sim_frame

    @property
    def sim_timestamp(self) -> float:
        """仿真时间戳"""
        return self._sim_timestamp

    @property
    def os_timestamp(self) -> float:
        """操作系统时间戳"""
        return self._os_timestamp

    @classmethod
    @abstractmethod
    def from_carla(cls, carla_input: Any) -> Self:
        """从 CARLA 输入数据中创建SimulatorOutput数据"""
        raise NotImplementedError