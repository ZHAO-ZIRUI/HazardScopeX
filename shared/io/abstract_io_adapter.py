from abc import ABC, abstractmethod
from typing_extensions import Self
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.simulator import CarlaSensor


class AbstractIOAdapter(ABC):
    """
    AbstractIOAdapter 抽象基类, 用于定义 IO 适配器的接口
    """

    @abstractmethod
    def bind_sensor_output(self, sensor: 'CarlaSensor') -> Self:
        pass