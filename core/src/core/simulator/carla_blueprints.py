from enum import Enum
from typing import Set


class CarlaBlueprints(Enum):
    """
    一个简单的枚举类用于简化对 CARLA 蓝图名（id）的使用
    """

    SENSOR_CAMERA_RGB = "sensor.camera.rgb"
    SENSOR_LIDAR_RAY_CAST = "sensor.lidar.ray_cast"
    SENSOR_OTHER_COLLISION = "sensor.other.collision"

    VEHICLE_TESLA_MODEL3 = "vehicle.tesla.model3"

    @staticmethod
    def get_event_sensor_blueprints_set() -> Set[str]:
        return {
            CarlaBlueprints.SENSOR_OTHER_COLLISION.value,
        }