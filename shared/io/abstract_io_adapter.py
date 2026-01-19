from abc import ABC, abstractmethod
from typing_extensions import Self
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.simulator import CarlaSensor
    from shared.simulator import CarlaContext


class AbstractIOAdapter(ABC):
    """
    AbstractIOAdapter 抽象基类, 用于定义 IO 适配器的接口
    """

    def __init__(self, context: 'CarlaContext'):
        self._context = context

    @abstractmethod
    def bind_sensor(self, sensor: 'CarlaSensor') -> Self:
        pass