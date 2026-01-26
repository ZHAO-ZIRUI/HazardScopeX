import carla
import numpy as np
from PIL import Image
import os

os.makedirs("./images", exist_ok=True)

client = carla.Client("localhost", 2000)
world = client.get_world()
bp_lib = world.get_blueprint_library()

# 设置夜晚天气（太阳高度角为负）
weather = carla.WeatherParameters()
weather.sun_altitude_angle = -45  # 夜晚
world.set_weather(weather)

# 欠曝等级和exposure_compensation值（负值）
exposure_levels = [-1.2, -2.4, -3.6]
level_names = ["I级", "II级", "III级"]

for level, exposure in enumerate(exposure_levels):
    # 创建车辆
    vehicle_bp = bp_lib.find("vehicle.tesla.model3")
    vehicle = world.spawn_actor(vehicle_bp, world.get_map().get_spawn_points()[1])
    
    # 创建摄像头并设置曝光补偿
    camera_bp = bp_lib.find("sensor.camera.rgb")
    camera_bp.set_attribute("exposure_mode", "manual")
    camera_bp.set_attribute("exposure_compensation", str(exposure))
    camera = world.spawn_actor(camera_bp, carla.Transform(carla.Location(z=1.5)), attach_to=vehicle)
    
    # 保存图片
    def save_image(image, level=level):
        array = np.frombuffer(image.raw_data, dtype=np.uint8).reshape((image.height, image.width, 4))
        array = array[:, :, [2, 1, 0]]  # BGRA -> RGB
        filename = f"./images/underexposure_{level_names[level]}.png"
        Image.fromarray(array).save(filename)
        print(f"Saved: {filename}")
    
    camera.listen(save_image)
    
    # 采集1帧
    world.tick()
    
    camera.destroy()
    vehicle.destroy()

print("Done!")
