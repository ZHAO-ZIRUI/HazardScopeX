import numpy as np
import random
import carla
import time
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
        vehicle: PlayerVehicle,
        *,
        path: str = "./images",
        exposure_level = 1, # 1 2 3
    ):
        super().__init__(context)
        self._path = path
        self._vehicle = vehicle
        self._sensor = None
        self._count = 0
        level_map = {
            1: {"name": "I级", "data": 1.2},
            2: {"name": "II级", "data": 2.4},
            3: {"name": "III级", "data": 3.6}
        }
        
        if exposure_level in level_map:
            info = level_map[exposure_level]
            self._exposure_level = info["data"]
            self._level_name = info["name"]
        else:
            raise ValueError(f"无效的等级: {exposure_level}")

    def bringup(self) -> None:
        
        # 设置夜晚天气（太阳高度角为负）
        world = self._context.world
        bp_lib = world.get_blueprint_library()
        weather = carla.WeatherParameters()
        weather.sun_altitude_angle = 45  # 白天
        world.set_weather(weather)
        os.makedirs("./images", exist_ok=True)
        camera_bp = bp_lib.find("sensor.camera.rgb")
        camera_bp.set_attribute("exposure_mode", "manual")
        camera_bp.set_attribute("exposure_compensation", str(self._exposure_level))
        self._sensor = self._vehicle.recreate_camera(camera_bp)
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        # print("hook:",self._sensor.hook_sensor_data_recv)

        return super().bringup()
    
    def on_sensor_data_recv(self, data: Image) -> Image:
        # print("Received image data for overexposure factor.")

        filename = f"./images/overexposure_{self._level_name}_{self._count}.png"
        data.to_file(filename)
        self._count += 1
        # print(f"Saved: {filename}")
        
        return data







# import numpy as np
# import random
# import carla
# from PIL import Image
# import os
# from collections import deque
# from shared.scenarios import Factor
# from shared.simulator import *
# from shared.data import Image


# class FactorCameraOverexposure(Factor):
#     NAME = 'F_CameraOverexposure'

#     def __init__(
#         self, 
#         context: CarlaContext, 
#         sensor: CarlaSensor,
#         *,
#         path: str = "./images",
#         exposure_level = 1, # 1 2 3
#         exposure_levels: list = [1.2, 2.4, 3.6],
#         level_names: list = ["I级", "II级", "III级"]
#     ):
#         super().__init__(context)
#         self._sensor = sensor
#         self._path = path
        
#         self._exposure_levels = exposure_levels
#         self._level_names = level_names

#     def bringup(self) -> None:
#         # self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
#         # 设置夜晚天气（太阳高度角为负）
#         world = self._context.world
#         bp_lib = world.get_blueprint_library()
#         weather = carla.WeatherParameters()
#         weather.sun_altitude_angle = 45  # 白天
#         world.set_weather(weather)
#         os.makedirs("./images", exist_ok=True)

#         for level, exposure in enumerate(self._exposure_levels):
#             # 创建车辆
#             vehicle_bp = bp_lib.find("vehicle.tesla.model3")
#             vehicle = world.spawn_actor(vehicle_bp, world.get_map().get_spawn_points()[1])
#             print("level:",level," exposure:",exposure)
#             # 创建摄像头并设置曝光补偿
#             camera_bp = bp_lib.find("sensor.camera.rgb")
#             camera_bp.set_attribute("exposure_mode", "manual")
#             camera_bp.set_attribute("exposure_compensation", str(exposure))
#             camera = world.spawn_actor(camera_bp, carla.Transform(carla.Location(z=1.5)), attach_to=vehicle)
            
#             # 保存图片
#             def save_image(image, level=level):
#                 array = np.frombuffer(image.raw_data, dtype=np.uint8).reshape((image.height, image.width, 4))
#                 array = array[:, :, [2, 1, 0]]  # BGRA -> RGB
#                 filename = f"./images/overexposure_{self._level_names[level]}.png"
#                 Image.fromarray(array).save(filename)
#                 print(f"Saved: {filename}")
            
#             camera.listen(save_image)
            
#             # 采集1帧
#             world.tick()
            
#             camera.destroy()
#             vehicle.destroy()
#         return super().bringup()