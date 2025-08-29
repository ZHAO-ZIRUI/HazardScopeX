from enum import Enum


class CarlaBlueprints(Enum):
    """
    一个简单的枚举类用于简化对 CARLA 蓝图名（id）的使用
    """

    SENSOR_CAMERA_RGB = "sensor.camera.rgb"
    SENSOR_LIDAR_RAY_CAST = "sensor.lidar.ray_cast"
    SENSOR_OTHER_COLLISION = "sensor.other.collision"