from enum import Enum
from typing import Literal


class CarlaSpawnPoints(Enum):
    """CARLA spawnpoint 枚举类
    
    """
    
    # # AI 控制器
    # CONTROLLER_AI_WALKER = 'controller.ai.walker'
    
    # # 传感器 - 相机
    # SENSOR_CAMERA_COSMOS_VISUALIZATION = 'sensor.camera.cosmos_visualization'
    # SENSOR_CAMERA_DEPTH = 'sensor.camera.depth'
    # SENSOR_CAMERA_DVS = 'sensor.camera.dvs'
    # SENSOR_CAMERA_INSTANCE_SEGMENTATION = 'sensor.camera.instance_segmentation'
    # SENSOR_CAMERA_NORMALS = 'sensor.camera.normals'
    # SENSOR_CAMERA_OPTICAL_FLOW = 'sensor.camera.optical_flow'
    # SENSOR_CAMERA_RGB = 'sensor.camera.rgb'
    # SENSOR_CAMERA_SEMANTIC_SEGMENTATION = 'sensor.camera.semantic_segmentation'
    
    @classmethod
    def straight_roads(cls) -> list[int]:
        # return [walker.value for walker in cls.__members__.values() if walker.value.startswith('walker.pedestrian.')]
        return 

    @classmethod
    def turning_roads(cls) -> list[int]:
        return
    
    @classmethod
    def entry_lanes(cls) -> list[int]:
        return
    
    @classmethod
    def export_lanes(cls) -> list[int]:
        return
    
    @classmethod
    def crossroads(cls) -> list[int]:
        return
    
    @classmethod
    def T_shaped_intersections(cls) -> list[int]:
        return

    @classmethod
    def circular_island_roads(cls) -> list[int]:
        return