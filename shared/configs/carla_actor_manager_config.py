from dataclasses import dataclass, field

from shared.configs import AbstractConfig


@dataclass
class CarlaActorManagerConfig(AbstractConfig):
    """
    CarlaActorManager 配置
    """
    spawn_wait_stable_threshold: float = field(default=0.0001, metadata={'route': 'actors/spawn/wait_stable_threshold'})
    spawn_wait_stable_timeout: float = field(default=3, metadata={'route': 'actors/spawn/wait_stable_timeout'})
    
    image_cc_depth: str = field(default='LogarithmicDepth', metadata={'route': 'actors/image_color_converter/depth'})
    image_cc_instance_segmentation: str = field(default='CityScapesPalette', metadata={'route': 'actors/image_color_converter/instance_segmentation'})
    image_cc_semantic_segmentation: str = field(default='CityScapesPalette', metadata={'route': 'actors/image_color_converter/semantic_segmentation'})