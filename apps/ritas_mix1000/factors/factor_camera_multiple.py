import numpy as np
import carla
import os
from collections import deque
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import Image
from shared.prefabs import PlayerVehicle


class FactorCameraMultiple(Factor):
    NAME = 'F_CameraMultiple'

    def __init__(
        self, 
        context: CarlaContext, 
        vehicle: PlayerVehicle,
        *,
        path: str = "./images",
        exposure_level = 0, # 1 2 3 -1 -2 -3
        aberration_level = 0, # 1 2 3
        cast_level = 0, # 1 2 3
    ):
        super().__init__(context)
        self._path = path
        self._vehicle = vehicle
        self._sensor = None
        self._count = 0

        self._exposure = 0
        self._aberration = 0
        self._cast = 0
        self._level_names = []

        level_map = {
            1: {"name": "I级", "exposure": 1.2, "cast": 4500, "aberration": 2},
            2: {"name": "II级", "exposure": 2.4, "cast": 3500, "aberration": 3.5},
            3: {"name": "III级", "exposure": 3.6, "cast": 2500, "aberration": 5},
            -1: {"name": "I级", "exposure": -1.2},
            -2: {"name": "II级", "exposure": -2.4},
            -3: {"name": "III级", "exposure": -3.6}
        }
        
        # 设置曝光等级
        if exposure_level != 0:
            if exposure_level in level_map:
                info = level_map[exposure_level]
                self._exposure = info["exposure"]
                self._level_names.append(f"曝光_{info['name']}")
            else:
                raise ValueError(f"无效的 Exposure 等级: {exposure_level}")
        
        # 设置色差等级
        if aberration_level != 0:
            if aberration_level in level_map and aberration_level > 0:
                info = level_map[aberration_level]
                self._aberration = info["aberration"]
                self._level_names.append(f"色差_{info['name']}")
            else:
                raise ValueError(f"无效的 Chromatic Aberration 等级: {aberration_level}")
        
        # 设置色偏等级
        if cast_level != 0:
            if cast_level in level_map and cast_level > 0:
                info = level_map[cast_level]
                self._cast = info["cast"]
                self._level_names.append(f"色偏_{info['name']}")
            else:
                raise ValueError(f"无效的 Color Cast 等级: {cast_level}")
            
        self._combined_level_name = "_".join(self._level_names) if self._level_names else "无效果"

    def bringup(self) -> None:
        world = self._context.world
        bp_lib = world.get_blueprint_library()
        weather = carla.WeatherParameters()
        weather.sun_altitude_angle = 45  # 白天
        world.set_weather(weather)
        os.makedirs(self._path, exist_ok=True)
        camera_bp = bp_lib.find("sensor.camera.rgb")
        if not self._exposure == 0:
            camera_bp.set_attribute("exposure_mode", "manual")
            camera_bp.set_attribute("exposure_compensation", str(self._exposure))
        if not self._aberration == 0:
            camera_bp.set_attribute("chromatic_aberration_intensity", str(self._aberration))
        if not self._cast == 0:
            camera_bp.set_attribute("temp", str(self._cast))
        self._sensor = self._vehicle.recreate_camera(camera_bp)
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)

        return super().bringup()
    
    def on_sensor_data_recv(self, data: Image) -> Image:
        filename = os.path.join(
            self._path, 
            f"camera_{self._combined_level_name}_{self._count}.png"
        )
        data.to_file(filename)
        self._count += 1

        return data