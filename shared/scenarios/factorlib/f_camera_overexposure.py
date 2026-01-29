import numpy as np
import carla
import os
from collections import deque
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import Image
from shared.prefabs import PlayerVehicle


class FactorCameraOverexposure(Factor):
    NAME = 'F_CameraOverexposure'

    def __init__(
        self, 
        context: CarlaContext, 
        ego_vehicle: CarlaVehicle,
        *,
        path: str = "./images",
        level = 1, # 1 2 3
    ):
        super().__init__(context, ego_vehicle)
        self._path = path
        self._vehicle = ego_vehicle
        self._sensor = None
        self._count = 0
        level_map = {
            1: {"name": "I级", "data": 1.2},
            2: {"name": "II级", "data": 2.4},
            3: {"name": "III级", "data": 3.6}
        }
        
        if level in level_map:
            info = level_map[level]
            self._exposure_level = info["data"]
            self._level_name = info["name"]
        else:
            raise ValueError(f"无效的等级: {level}")

    def bringup(self) -> None:
        world = self._context.world
        bp_lib = world.get_blueprint_library()
        weather = carla.WeatherParameters()
        weather.sun_altitude_angle = 45  # 白天
        world.set_weather(weather)
        os.makedirs("./images", exist_ok=True)
        camera_bp = bp_lib.find("sensor.camera.rgb")
        camera_bp.set_attribute("exposure_mode", "manual")
        camera_bp.set_attribute("exposure_compensation", str(self._exposure_level))
        self._sensor = self._vehicle.respawn_front_camera(camera_bp)
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)

        return super().bringup()
    
    def on_sensor_data_recv(self, data: Image) -> Image:
        filename = f"./images/overexposure_{self._level_name}_{self._count}.png"
        data.to_file(filename)
        self._count += 1

        return data




