from abc import ABC, abstractmethod
from typing_extensions import Self

from shared.simulator import CarlaSensor


class IOAdapter(ABC):
    """
    IO 适配器, 用于将仿真器的输入输出转换
    """

    @abstractmethod
    def bind_sensor_output(self, sensor: CarlaSensor) -> Self:
        pass