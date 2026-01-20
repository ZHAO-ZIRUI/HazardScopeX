from abc import ABC, abstractmethod
from typing import Any
from typing_extensions import Self
from shared.data import BaseData



class SimulatorInput(BaseData, ABC):
    """
    仿真器的输入数据
    
    该类仅提供与 SimulatorOutput 的对等抽象
    """
    
    @classmethod
    @abstractmethod
    def from_ros2(cls, ros2_msg: Any) -> Self | None:
        """从 ROS2 消息中创建数据"""
        raise NotImplementedError