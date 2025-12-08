from dataclasses import dataclass, field

from shared.configs import AbstractConfig


@dataclass
class CarlaRecorderConfig(AbstractConfig):
    """
    CarlaRecorder 配置
    """
    path: str = field(default='recorders', metadata={'route': 'recorder/path'})