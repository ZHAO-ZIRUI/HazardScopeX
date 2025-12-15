from dataclasses import dataclass, field

from shared.configs import AbstractConfig


@dataclass
class CarlaDatasetDumperConfig(AbstractConfig):
    """
    CarlaDatasetDumper 配置
    """
    path: str = field(default='export', metadata={'route': 'dataset/path'})
    safe_memory_usage_threshold: float = field(default=0.95, metadata={'route': 'dataset/safe_memory_usage_threshold'})