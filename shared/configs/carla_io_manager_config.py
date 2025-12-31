from dataclasses import dataclass, field

from shared.configs import AbstractConfig


@dataclass
class CarlaIOManagerConfig(AbstractConfig):
    """
    CarlaIOManager 配置
    """
    shared_memory_domain: str = field(default='hazard_scope', metadata={'route': 'io/shared_memory/domain'})
    shared_memory_default_size_mb: int = field(default=30, metadata={'route': 'io/shared_memory/default_size_mb'})
    ros2_node_name: str = field(default='hazard_scope_ros2_node', metadata={'route': 'io/ros2/node_name'})
    ros2_node_qos: int = field(default=10, metadata={'route': 'io/ros2/node_qos'})